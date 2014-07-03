# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 GNS3 Technologies Inc.
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

# __version__ is a human-readable version number.

# __version_info__ is a four-tuple for programmatic comparison. The first
# three numbers are the components of the version number. The fourth
# is zero for an official release, positive for a development branch,
# or negative for a release candidate or beta (after the base version
# number has been incremented)

"""
Monitors communication with the GNS3 client. Will terminate the instance if 
communication is lost.
"""

import os
import sys
import time
import getopt
import datetime
import logging
import fcntl
import signal
import configparser

SCRIPT_NAME = os.path.basename(__file__)

#Is the full path when used as an import
SCRIPT_PATH = os.path.dirname(__file__)

if not SCRIPT_PATH:
    SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(
        sys.argv[0])))


EXTRA_LIB = "%s/modules" % (SCRIPT_PATH)


LOG_NAME = "gns3dms"
log = None

sys.path.append(EXTRA_LIB)

import daemon

my_daemon = None 

usage = """
USAGE: %s

Options:

  -d, --debug         Enable debugging
  -v, --verbose       Enable verbose logging
  -h, --help          Display this menu :)

  --cloud_api_key <api_key>  Rackspace API key           
  --cloud_user_name
  
  --deadtime          How long can the communication lose exist before we 
                      shutdown this instance.

  -k                  Kill previous instance running in background
  --background        Run in background

""" % (SCRIPT_NAME)

# Parse cmd line options
def parse_cmd_line(argv):
    """
    Parse command line arguments

    argv: Pass in cmd line arguments
    """

    short_args = "dvhk:"
    long_args = ("debug",
                    "verbose",
                    "help",
                    "cloud_user_name=",
                    "cloud_api_key=",
                    "deadtime=",
                    "background",
                    )
    try:
        opts, extra_opts = getopt.getopt(argv[1:], short_args, long_args)
    except getopt.GetoptError as e:
        print("Unrecognized command line option or missing required argument: %s" %(e))
        print(usage)
        sys.exit(2)

    cmd_line_option_list = {}
    cmd_line_option_list["debug"] = False
    cmd_line_option_list["verbose"] = True
    cmd_line_option_list["cloud_user_name"] = None
    cmd_line_option_list["cloud_api_key"] = None
    cmd_line_option_list["deadtime"] = 30 #minutes
    cmd_line_option_list["shutdown"] = False
    cmd_line_option_list["daemon"] = False

    get_gns3secrets(cmd_line_option_list)

    for opt, val in opts:
        if (opt in ("-h", "--help")):
            print(usage)
            sys.exit(0)
        elif (opt in ("-d", "--debug")):
            cmd_line_option_list["debug"] = True
        elif (opt in ("-v", "--verbose")):
            cmd_line_option_list["verbose"] = True
        elif (opt in ("--cloud_user_name")):
            cmd_line_option_list["cloud_user_name"] = val
        elif (opt in ("--cloud_api_key")):
            cmd_line_option_list["cloud_api_key"] = val
        elif (opt in ("--deadtime")):
            cmd_line_option_list["deadtime"] = val
        elif (opt in ("-k")):
            cmd_line_option_list["shutdown"] = True
        elif (opt in ("--background")):
            cmd_line_option_list["daemon"] = True

    if cmd_line_option_list["cloud_user_name"] is None:
        print("You need to specify a username!!!!")
        print(usage)
        sys.exit(2)

    if cmd_line_option_list["cloud_api_key"] is None:
        print("You need to specify an apikey!!!!")
        print(usage)
        sys.exit(2)

    return cmd_line_option_list

def get_gns3secrets(cmd_line_option_list):
    """
    Load cloud credentials from .gns3secrets
    """

    gns3secret_paths = [
        os.path.expanduser("~/"),
        SCRIPT_PATH,
    ]

    config = configparser.ConfigParser()

    for gns3secret_path in gns3secret_paths:
        gns3secret_file = "%s/.gns3secrets.conf" % (gns3secret_path)
        if os.path.isfile(gns3secret_file):
            config.read(gns3secret_file)

    try:
        for key, value in config.items("Cloud"):
            cmd_line_option_list[key] = value.strip()
    except configparser.NoSectionError:
        pass


def set_logging(cmd_options):
    """
    Setup logging and format output
    """
    log = logging.getLogger("%s" % (LOG_NAME))
    log_level = logging.INFO
    log_level_console = logging.WARNING

    if cmd_options['verbose'] == True:
        log_level_console = logging.INFO

    if cmd_options['debug'] == True:
        log_level_console = logging.DEBUG
        log_level = logging.DEBUG

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_log = logging.StreamHandler()
    console_log.setLevel(log_level_console)
    console_log.setFormatter(formatter)

    syslog_hndlr = logging.SysLogHandler(facility=LOG_KERN)
    
    log.setLevel(log_level)
    log.addHandler(console_log)
    log.addHandler(syslog_hndlr)

    return log

def send_shutdown(pid_file):
    with open(pid_file, 'r') as pidf:
        pid = int(pidf.readline().strip())
        pidf.close()


    os.kill(pid, 15)

def main():

    global log
    global my_daemon
    options = parse_cmd_line(sys.argv)
    log = set_logging(options)

    def _shutdown(signalnum=None, frame=None):
        """
        Handles the SIGINT and SIGTERM event, inside of main so it has access to
        the log vars.
        """

        log.warning("Received shutdown signal")
        

    pid_file = "%s/%s.pid" % (SCRIPT_PATH, SCRIPT_NAME)

    if options["shutdown"]:
        send_shutdown(pid_file)
        sys.exit(0)

    if options["daemon"]:
        print("Starting in background ...\n")
        my_daemon = MyDaemon(pid_file, options)

    # Setup signal to catch Control-C / SIGINT and SIGTERM
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    log.debug("Using settings:")
    for key, value in iter(sorted(options.items())):
        log.debug("%s : %s" % (key, value))
    
    log.warning("Starting ...")

    if my_daemon:
        my_daemon.start()
    else:
        pass


class MyDaemon(daemon.daemon):
    def run(self):
        pass



if __name__ == "__main__":
    result = main()
    sys.exit(result)


