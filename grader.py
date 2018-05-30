#!/usr/bin/env python3.6

#
# Example for a complex grading script that utilizes all features of the moodleteacher library.
#
# TODO:
# - Remember last window size on next start

import sys

from moodleteacher import MoodleConnection, MoodleAssignments, MoodleUser, MoodleSubmissionFile
from moodleteacher.preview import show_preview


def handle_submission(submission):
    '''
        Handles the teacher action for a single student submission.
    '''
    print("#" * 78)
    # Submission has either textfield content or uploaed files, and was not graded so far.
    # Fetch user details of the submitter
    user_details = MoodleUser(conn, submission.userid)
    print("Submission {0.id} by {1.fullname}".format(submission, user_details))
    # Ask user what to do
    inp = 'x'
    while inp != 'g' and inp != '':
        inp = input(
            "Your options: Enter (g)rading. Show (p)review. S(k)ip this submission.\nYour choice [g]:")
        if inp == 'p':
            if submission.textfield:
                files = [MoodleSubmissionFile(
                    filename='(Moodle Text Box)', content=submission.textfield, content_type='text/html')]
            else:
                files = []
            files += MoodleSubmissionFile.from_urls(conn, submission.files)
            if not show_preview(user_details.fullname, files):
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

    # Retrieve list of assignments objects.
    print("Fetching list of assignments ...")
    assignments = MoodleAssignments(conn)

    # Go through assignments, sorted by deadline (oldest first).
    for assignment in sorted(assignments, key=lambda x: x.deadline):
        if not assignment.course.can_grade:
            print("Skipping '{0.name}', you have no rights to grade it.".format(
                assignment))
            continue
        if not assignment.deadline_over():
            print("Skipping '{0.name}', still open.".format(
                assignment))
            continue
        print("Assignment '{0.name}' in '{0.course}', due to {0.deadline}:".format(
            assignment))
        submissions = assignment.submissions()
        gradable = [sub for sub in submissions if not sub.is_empty(
        ) and sub.gradingstatus == sub.NOT_GRADED]
        if len(sys.argv) > 1 and sys.argv[1] == "overview":
            print("%u gradable submissions" % len(gradable))
        else:
            for sub in gradable:
                handle_submission(sub)
