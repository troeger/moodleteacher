'''
A demonstration for automated validation of submissions in Moodle
with the help of this library.

We assume that Moodle credentials are cached from an earlier
interactive run. Alternatively, you need to set the according environment
variables.

For this example, the moodle course must have a folder containing the
validation scripts. This folder should be hidden for students in the UI,
but is still acessible through the API. Each Python file in this
folder is a validator for a specific assignment, where the filename stands
for the assignment ID.

This script downloads all validators and runs them against all matching
submissions.
'''

import sys
import os
import argparse
import logging

# Allow execution of script from project root, based on the library
# source code
sys.path.append(os.path.realpath('.'))

from moodleteacher.connection import MoodleConnection      # NOQA
from moodleteacher.courses import MoodleCourse             # NOQA
from moodleteacher.jobs import ValidationJob               # NOQA

# Enable library debug logging on screen
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger('moodleteacher')
logger.addHandler(handler)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--courseid", help="Course ID (check view.php?id=...).", required=True, type=int)
    parser.add_argument(
        "-f", "--folderid", help="ID of the folder with validators (check view.php?id=...).", required=True, type=int)
    args = parser.parse_args()

    conn = MoodleConnection(interactive=True)
    course = MoodleCourse.from_course_id(conn, args.courseid)

    # Get assignments for course
    assignments = course.assignments()
    print("Course {0} with {1} assignments".format(course, len(assignments)))

    # Get folder
    for folder in course.get_folders():
        if folder.id_ == args.folderid:
            validators_folder = folder
            print("Folder: {0}".format(validators_folder))

    # Scan validator files in folder, determine according assignment and check if it has submissions
    for validator in validators_folder.files:
        validator_assignment_name = validator.name.split('.')[0]
        for assignment in assignments:
            if assignment.name.strip().lower() == validator_assignment_name.strip().lower():
                submissions = assignment.submissions()
                print("Assignment {0} with {1} submissions.".format(assignment, len(submissions)))
                for submission in submissions:
                    print("Submission to be validated: {0}".format(submission))
                    job = ValidationJob(submission, validator)
                    job.start(log_level=logging.INFO)
