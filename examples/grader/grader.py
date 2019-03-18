#!/usr/bin/env python3
#
# Example for a complex grading script that utilizes all features of the moodleteacher library.
#
# TODO:
# - Remember last window size on next start

import argparse
import sys
import os
# Allow execution of script from project root, based on the library
# source code
sys.path.append(os.path.realpath('.'))


from moodleteacher.connection import MoodleConnection      # NOQA
from moodleteacher.assignments import MoodleAssignments    # NOQA
from moodleteacher.files import MoodleFile                 # NOQA
from moodleteacher.preview import show_preview             # NOQA


def handle_submission(submission):
    '''
        Handles the teacher action for a single student submission.
    '''
    print("#" * 78)
    # Submission has either textfield content or uploaed files, and was not graded so far.
    if submission.is_group_submission:
        group = submission.assignment.course.get_group(submission.groupid)
        if group:
            members = [u.fullname for u in submission.get_group_members()]
            print("Submission {0.id} by group {1} - {2}".format(submission, group, members))
            display_name = group.fullname
        else:
            print("Submission {0.id} by unknown group with ID {0.groupid}".format(submission))
            display_name = "Group {0}".format(submission.groupid)
    else:
        user = submission.assignment.course.users[submission.userid]
        print("Submission {0.id} by {1.fullname} ({1.id})".format(submission, user))
        display_name = user.fullname
    # Ask user what to do
    inp = 'x'
    while inp != 'g' and inp != '':
        inp = input(
            "Your options: Enter (g)rading. Show (p)review. S(k)ip this submission.\nYour choice [g]:")
        if inp == 'p':
            if submission.textfield:
                fake_file = MoodleFile.from_local_data(
                    name='(Moodle Text Box)',
                    content=submission.textfield,
                    content_type='text/html')
                submission.files.append(fake_file)
            if not show_preview(display_name, submission.files):
                print("Sorry, preview not possible.")
        if inp == 'k':
            return
    if assignment.allows_feedback_comment:
        comment = input("Feedback for student:")
    else:
        comment = ""
    grade = input("Grade:")
    if grade != "":
        print("Saving grade '{0}'...".format(float(grade)))
        submission.save_grade(grade, comment)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG)

    # Prepare connection to your Moodle installation.
    # The flag makes sure that the user is asked for credentials, which are then
    # stored in ~/.moodleteacher for the next time.
    conn = MoodleConnection(interactive=True)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--overview", help="No grading, just give an overview.", default=False, action="store_true")
    parser.add_argument(
        "-c", "--courseid", help="Limit to this course ID (check view.php?id=...).", default=[], action='append')
    parser.add_argument("-a", "--assignmentid",
                        help="Limit to this assignment ID (check view.php?id=...).", default=[], action='append')
    parser.add_argument("-g", "--gradableonly",
                        help="Limit to assignments you have grading rights for.", default=False, action="store_true")
    args = parser.parse_args()

    # Retrieve list of assignments objects.
    print("Fetching list of assignments ...")
    course_filter = [int(courseid) for courseid in args.courseid]
    if course_filter is []:
        course_filter = None
    assignment_filter = [int(assignmentid) for assignmentid in args.assignmentid]
    if assignment_filter is []:
        assignment_filter = None
    assignments = MoodleAssignments(conn, course_filter=course_filter, assignment_filter=assignment_filter)

    # Go through assignments, sorted by deadline (oldest first).
    assignments = sorted(assignments, key=lambda x: x.deadline)
    for assignment in assignments:
        if (not args.gradableonly or assignment.course.can_grade):
            submissions = assignment.submissions()
            gradable = [sub for sub in submissions if not sub.is_empty(
            ) and sub.gradingstatus == sub.NOT_GRADED]
            if args.overview:
                print("{1} gradable submissions: '{0.name}' ({0.id}) in '{0.course}' ({0.course.id}), {2}".format(
                    assignment, len(gradable), 'geschlossen' if assignment.deadline_over() else 'offen'))
            else:
                print("Assignment '{0.name}' in '{0.course}', due to {0.deadline}:".format(
                    assignment))
                if not assignment.deadline_over():
                    print("  Skipping it, still open.".format(
                        assignment))
                    continue
                for sub in gradable:
                    handle_submission(sub)
