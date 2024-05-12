#!/usr/bin/env python3
#
# Example for working with Moodle users
#

import argparse
import sys
import os
# Allow execution of script from project root, based on the library
# source code
sys.path.append(os.path.realpath('.'))


from moodleteacher.connection import MoodleConnection      # NOQA
from moodleteacher.users import MoodleUser      # NOQA

if __name__ == '__main__':
    #import logging
    #logging.basicConfig(level=logging.DEBUG)

    # Prepare connection to your Moodle installation.
    # The flag makes sure that the user is asked for credentials, which are then
    # stored in ~/.moodleteacher for the next time.
    conn = MoodleConnection(interactive=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("users", nargs="*", type=str)
    args = parser.parse_args()

    for username in args.users:
        user = MoodleUser.from_userid(conn, username)
        print(user)
