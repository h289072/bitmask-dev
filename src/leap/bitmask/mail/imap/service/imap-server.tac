#!/usr/bin/env python
# -*- coding: utf-8 -*-
# imap-server.tac
# Copyright (C) 2013,2014 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
TAC file for initialization of the imap service using twistd.

Use this for debugging and testing the imap server using a native reactor.

For now, and for debugging/testing purposes, you need
to pass a config file with the following structure:

[leap_mail]
userid = 'user@provider'
uuid = 'deadbeefdeadabad'
passwd = 'supersecret' # optional, will get prompted if not found.
"""
# TODO -- this .tac file should be deprecated in favor of bitmask.core.bitmaskd
import ConfigParser
import getpass
import os
import sys

from twisted.application import service, internet

from leap.bitmask.util import get_gpg_bin_path
from leap.bitmask.keymanager import KeyManager
from leap.bitmask.mail.imap.service import LeapIMAPFactory
from leap.soledad.client import Soledad



# TODO should get this initializers from some authoritative mocked source
# We might want to put them the soledad itself.

def initialize_soledad(uuid, email, passwd,
                       secrets, localdb,
                       gnupg_home, tempdir):
    """
    Initializes soledad by hand

    :param email: ID for the user
    :param gnupg_home: path to home used by gnupg
    :param tempdir: path to temporal dir
    :rtype: Soledad instance
    """
    server_url = "http://provider"
    cert_file = ""

    soledad = Soledad(
        uuid,
        passwd,
        secrets,
        localdb,
        server_url,
        cert_file,
        syncable=False)

    return soledad

######################################################################
# Remember to set your config files, see module documentation above!
######################################################################

print "[+] Running LEAP IMAP Service"


bmconf = os.environ.get("LEAP_MAIL_CONFIG", "")
if not bmconf:
    print ("[-] Please set LEAP_MAIL_CONFIG environment variable "
           "pointing to your config.")
    sys.exit(1)

SECTION = "leap_mail"
cp = ConfigParser.ConfigParser()
cp.read(bmconf)

userid = cp.get(SECTION, "userid")
uuid = cp.get(SECTION, "uuid")
passwd = unicode(cp.get(SECTION, "passwd"))

# XXX get this right from the environment variable !!!
port = 1984

if not userid or not uuid:
    print "[-] Config file missing userid or uuid field"
    sys.exit(1)

if not passwd:
    passwd = unicode(getpass.getpass("Soledad passphrase: "))


secrets = os.path.expanduser("~/.config/leap/soledad/%s.secret" % (uuid,))
localdb = os.path.expanduser("~/.config/leap/soledad/%s.db" % (uuid,))

# XXX Is this really used? Should point it to user var dirs defined in xdg?
gnupg_home = "/tmp/"
tempdir = "/tmp/"

###################################################

# Ad-hoc soledad/keymanager initialization.

print "[~] user:", userid
soledad = initialize_soledad(uuid, userid, passwd, secrets,
                             localdb, gnupg_home, tempdir, userid=userid)
km_args = (userid, "https://localhost", soledad)
km_kwargs = {
    "token": "",
    "ca_cert_path": "",
    "api_uri":  "",
    "api_version": "",
    "uid": uuid,
    "gpgbinary": get_gpg_bin_path()
}
keymanager = KeyManager(*km_args, **km_kwargs)

##################################################

# Ok, let's expose the application object for the twistd application
# framework to pick up from here...


def getIMAPService():
    soledad_sessions = {userid: soledad}
    factory = LeapIMAPFactory(soledad_sessions)
    return internet.TCPServer(port, factory, interface="localhost")


application = service.Application("LEAP IMAP Application")
service = getIMAPService()
service.setServiceParent(application)
