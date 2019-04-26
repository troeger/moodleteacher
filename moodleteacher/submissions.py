from .requests import MoodleRequest
from .files import MoodleFile

import logging
logger = logging.getLogger('moodleteacher')


GRADED = 'graded'
NOT_GRADED = 'notgraded'
NEW = 'new'
SUBMITTED = 'submitted'


class MoodleSubmission():
    """
        A single student submission in Moodle.
    """

    def __init__(self, conn=None, submission_id=None, assignment=None, user_id=None, group_id=None, status=None, gradingstatus=None, textfield=None, files=[]):
        self.conn = conn
        self.id_ = submission_id
        self.assignment = assignment
        self.userid = user_id
        self.groupid = group_id
        self.status = status
        self.gradingstatus = gradingstatus
        self.textfield = textfield
        self.files = files

    @classmethod
    def from_local_file(cls, assignment, fpath):
        """
        Creation of a local-only fake submission object.
        Mainly needed for the test suite.
        """
        return cls(conn=assignment.conn, assignment=assignment, files=[MoodleFile.from_local_file(fpath)])

    def __str__(self):
        num_files = len(self.files)
        text = "Submission {0.id_} by user {0.userid}, status: {0.gradingstatus}, files: {1}, ".format(
            self, num_files)
        if self.textfield:
            text += "with notes"
        else:
            text += "without notes"
        return(text)

    def parse_plugin_json(self, raw_json):
        """
        Parses a plugin block from Moodle JSON and updates the object
        accordingly.
        """
        files = []
        textfield = None
        for plugin in raw_json:
            if plugin['type'] == 'file':
                for fileinfo in plugin['fileareas'][0]['files']:
                    moodle_file = MoodleFile.from_url(
                        conn=self.conn,
                        url=fileinfo['fileurl'],
                        name=fileinfo['filename'],
                        time_modified=fileinfo['timemodified'],
                        mime_type=fileinfo['mimetype'])
                    files.append(moodle_file)
            elif plugin['type'] == 'onlinetext':
                textfield = plugin['editorfields'][0]['text']
        self.files = files
        self.textfield = textfield

    def is_empty(self):
        return len(self.files) == 0 and not self.textfield

    def is_graded(self):
        return self.gradingstatus == GRADED

    def is_group_submission(self):
        return self.userid == 0 and self.groupid != 0

    def get_group_members(self):
        assert(self.is_group_submission())
        return self.assignment.course.get_group_members(self.groupid)

    def load_feedback(self):
        """
        Retreives the current feedback for this submission from the Moodle server.
        """
        params = {'assignid': self.assignment.id_,
                  'userid': self.userid}
        response = MoodleRequest(
            self.conn, 'mod_assign_get_submission_status').post(params=params).json()
        try:
            plugins = response['feedback']['plugins']
            for plugin in plugins:
                if plugin['type'] == 'comments':
                    return plugin['editorfields'][0]['text']
        except Exception:
            pass
        return None

    def save_feedback(self, feedback):
        """
        Saves new feedback information on the Moodle server.

        See also https://moodle.org/mod/forum/discuss.php?d=384108.
        """
        logger.debug("Saving feedback information only.")
        self.save_grade(grade=-99999, feedback=feedback)
        return ""

    def save_grade(self, grade, feedback=None):
        """
        Saves new grading information for this student on the Moodle server, and sets the workflow
        state to "graded".
        """
        # You can only give text feedback if your assignment is configured accordingly
        if feedback is not None and not self.assignment.allows_feedback_comment:
            logger.error("Could not save feedback, assignment does not allow feedback comments. Please check your assignment settings in Moodle.")
            return

        if self.is_group_submission():
            userid = self.get_group_members()[0].id_
        else:
            userid = self.userid

        data = {'assignmentid': self.assignment.id_,
                  'userid': userid,
                  'workflowstate': GRADED,
                  'attemptnumber': -1,
                  'addattempt': int(True),
                  'grade': float(grade) if grade else '',
                  # always apply grading to team
                  # if the assignment has no group submission, this has no effect.
                  'applytoall': int(True),
                  'plugindata[assignfeedbackcomments_editor][text]': str(feedback) if feedback else "",
                  # //content format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
                  'plugindata[assignfeedbackcomments_editor][format]': 1
                  }

        response = MoodleRequest(
            self.conn, 'mod_assign_save_grade').post(data=data).json()
        logger.debug("Response from grading update: {0}".format(response))
