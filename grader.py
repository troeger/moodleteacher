#!/usr/bin/env python3.6

#
# Example for a complex grading script that utilizes all features of the moodleteacher library.
#

from moodleteacher import MoodleConnection, MoodleAssignments, MoodleUser, MoodleSubmissionFile
from moodleteacher.preview import show_html_preview, show_file_preview

def handle_submission(submission):
    '''
        Handles the teacher action for a single student submission.
    '''
    print("#"*78)
    # Submission has either textfield content or uploaed files, and was not graded so far.
    # Fetch user details of the submitter
    user_details = MoodleUser(conn, submission.userid)
    print("Submission {0.id} by {1.fullname}".format(submission, user_details))
    # Handling grading depending on the submission content
    if submission.textfield:
            # Textfield entries from students are given as as HTML snippet
            show_html_preview(user_details.fullname, submission.textfield)
    if submission.files:
        for file_url in submission.files:
            # Download student upload to this computer
            f = MoodleSubmissionFile(conn, file_url)
            # Show details of the file, especially the content type.
            print("Submission file "+str(f))
            # Ask what to do with it.
            inp = input("Your options:\nRun (l)ocally as shell script.\nRun (r)emotely as shell script.\nShow (p)review.\nS(k)ip this submission.\nYour choice:")
            if inp == 'l':
                print(f.as_text())
                # Store file in temporary file and run it with bash locally.
                f.run_shellscript_local()
            if inp == 'r':
                print(f.as_text())
                # Store file in temporary file on remote computer (SCP) and run it with bash remotely (SSH).
                f.run_shellscript_remote('ptroeger', 'dbl65.beuth-hochschule.de', '/tmp')
            if inp == 'p':
                # Show file preview, depending on content type (pdf, text, ...)
                if not show_file_preview(user_details.fullname, f):
                    print("Sorry, preview not possible for this file type. Skipping submission.")
                    return
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
    #import logging
    #logging.basicConfig(level=logging.DEBUG)

    # Prepare connection to your Moodle installation.
    # The flag makes sure that the user is asked for credentials, which are then
    # stored in ~/.moodleteacher for the next time.
    conn = MoodleConnection(interactive=True)

    # Retrieve list of assignments objects. 
    print("Fetching list of assignments ...")
    assignments = MoodleAssignments(conn)

    # Go through assignments, sorted by deadline (oldest first).
    for assignment in sorted(assignments, key=lambda x:x.deadline):
        print("Assignment '{0.name}' in '{0.course}', due to {0.deadline}.".format(assignment))
        if not assignment.course.can_grade:
            print("  Skipping assignment, you have no rights to grade it.")
            continue
        if not assignment.deadline_over():
            print("  Skipping assignment, still open.")
            continue
        for sub in assignment.submissions():
            if not sub.is_empty() and sub.gradingstatus == sub.NOT_GRADED:
                handle_submission(sub)
