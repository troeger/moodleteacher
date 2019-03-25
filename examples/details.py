#!/usr/bin/env python3
#
# Example for retrieving submission details
#

import argparse
import sys
import os
# Allow execution of script from project root, based on the library
# source code
sys.path.append(os.path.realpath('.'))


from moodleteacher.connection import MoodleConnection      # NOQA
from moodleteacher.courses import MoodleCourse      # NOQA

if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG)

    # Prepare connection to your Moodle installation.
    # The flag makes sure that the user is asked for credentials, which are then
    # stored in ~/.moodleteacher for the next time.
    conn = MoodleConnection(interactive=True)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--courseid", help="Course ID (check view.php?id=...).", required=True, type=int)
    args = parser.parse_args()

    course = MoodleCourse.from_course_id(conn, args.courseid)

    for assignment in course.assignments():
        for submission in assignment.submissions():
            print(submission)
            for f in submission.files:
                print(f)
