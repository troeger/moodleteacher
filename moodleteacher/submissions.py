from .requests import MoodleRequest
from .files import MoodleFile


class MoodleSubmission():
    '''
        A single student submission in Moodle.
    '''
    GRADED = 'graded'
    NOT_GRADED = 'notgraded'

    def __init__(self, conn=None, submission_id=None, assignment=None, user_id=None, group_id=None, status=None, gradingstatus=None, textfield=None, files=None, raw_json=None):
        self.conn = conn
        self.id_ = submission_id
        self.assignment = assignment
        self.userid = user_id
        self.groupid = group_id
        self.status = status
        self.gradingstatus = gradingstatus
        self.textfield = textfield
        self.files = files
        self.raw_json = raw_json

    @classmethod
    def from_local_file(cls, fpath):
        '''
        Creation of a local-only fake submission object.
        Mainly needed for the test suite.
        '''
        return cls(files=[MoodleFile.from_local_file(fpath)])

    @classmethod
    def from_assignment_json(cls, assignment, raw_json):
        '''
        Creation of a submission object based on JSON data
        from the Moodle server that was returned together with
        assignment information.
        '''
        files = []
        textfield = None
        for plugin in raw_json['plugins']:
            if plugin['type'] == 'file':
                for fileinfo in plugin['fileareas'][0]['files']:
                    moodle_file = MoodleFile.from_url(
                        conn=assignment.conn,
                        url=fileinfo['fileurl'],
                        name=fileinfo['filename'])
                    files.append(moodle_file)
            elif plugin['type'] == 'onlinetext':
                textfield = plugin['editorfields'][0]['text']

        return cls(conn=assignment.conn,
                   submission_id=raw_json['id'],
                   assignment=assignment,
                   user_id=raw_json['userid'],
                   group_id=raw_json['groupid'],
                   status=raw_json['status'],
                   gradingstatus=raw_json['gradingstatus'],
                   textfield=textfield,
                   files=files,
                   raw_json=raw_json)

    def __str__(self):
        num_files = len(self.files)
        text = "Abgabe {0.id_} durch Nutzer {0.userid} ({0.gradingstatus}), {1} Dateien, ".format(
            self, num_files)
        if self.textfield:
            text += "mit Text"
        else:
            text += "ohne Text"
        return(text)

    def is_empty(self):
        return len(self.files) == 0 and not self.textfield

    def is_group_submission(self):
        return self.userid == 0 and self.groupid != 0

    def get_group_members(self):
        assert(self.is_group_submission())
        return self.assignment.course.get_group_members(self.groupid)

    def save_grade(self, grade, feedback="", applytoall=True):
        # You can only give text feedback if your assignment is configured accordingly
        assert(feedback is "" or self.assignment.allows_feedback_comment)
        if self.is_group_submission():
            userid = self.get_group_members()[0].id_
        else:
            userid = self.userid
        params = {'assignmentid': self.assignment.id_,
                  'userid': userid,
                  'grade': float(grade),
                  'attemptnumber': -1,
                  'addattempt': int(True),
                  'workflowstate': self.GRADED,
                  # always apply grading to team
                  # if the assignment has no group submission, this has no effect.
                  'applytoall': int(True),
                  'plugindata[assignfeedbackcomments_editor][text]': str(feedback),
                  # //content format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
                  'plugindata[assignfeedbackcomments_editor][format]': 2
                  }
        MoodleRequest(self.conn, 'mod_assign_save_grade').post(params)


class MoodleSubmissions(list):
    '''
        A list of MoodleSubmission instances.
    '''

    conn = None

    @classmethod
    def from_assignment(cls, assignment):
        '''
        Create a list of submissions for an assignment.
        '''
        o = cls()
        o.conn = assignment.conn
        params = {'assignmentids[0]': assignment.id_}
        response = MoodleRequest(
            o.conn, 'mod_assign_get_submissions').post(params).json()
        for response_assignment in response['assignments']:
            assert(response_assignment['assignmentid'] == assignment.id_)
            for subm_data in response_assignment['submissions']:
                submission = MoodleSubmission.from_assignment_json(
                    assignment, subm_data)
                o.append(submission)
        return o

    def __str__(self):
        return "\n".join([str(sub) for sub in self])
