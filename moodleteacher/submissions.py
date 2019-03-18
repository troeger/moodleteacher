from .requests import MoodleRequest
from .files import MoodleFile


class MoodleSubmission():
    '''
        A single student submission in Moodle.
    '''
    GRADED = 'graded'
    NOT_GRADED = 'notgraded'

    files = []
    assignment = None
    conn = None
    raw_json = None
    id = None
    userid = None
    groupid = None
    status = None
    gradingstatus = None
    textfield = None

    def __init__(self, fpath):
        '''
        Creation of a local-only fake submission object.
        Mainly needed for the test suite.
        '''
        self.files = [MoodleFile.from_local_file(fpath)]

    def __init__(self, conn, assignment, raw_json):
        '''
        Creation of a submission object based on JSON data
        from the Moodle server.
        '''
        self.assignment = assignment
        self.conn = conn
        self.raw_json = raw_json
        self.id = raw_json['id']
        self.userid = raw_json['userid']
        self.groupid = raw_json['groupid']
        self.status = raw_json['status']
        self.gradingstatus = raw_json['gradingstatus']
        file_urls = []
        self.textfield = None
        for plugin in raw_json['plugins']:
            if plugin['type'] == 'file':
                filelist = plugin['fileareas'][0]['files']
                for f in filelist:
                    file_urls.append(f['fileurl'])
            if plugin['type'] == 'onlinetext':
                self.textfield = plugin['editorfields'][0]['text']
        for file_url in file_urls:
            self.files.append(MoodleFile.from_url(conn, file_url))

    def __str__(self):
        num_files = len(self.files)
        text = "Abgabe {0.id} durch Nutzer {0.userid} ({0.gradingstatus}), {1} Dateien, ".format(
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
            userid = self.get_group_members()[0].id
        else:
            userid = self.userid
        params = {'assignmentid': self.assignment.id,
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

    def __init__(self, conn, assignment):
        params = {'assignmentids[0]': assignment.id}
        response = MoodleRequest(
            conn, 'mod_assign_get_submissions').post(params).json()
        for response_assignment in response['assignments']:
            assert(response_assignment['assignmentid'] == assignment.id)
            for subm_data in response_assignment['submissions']:
                self.append(MoodleSubmission(conn, assignment, subm_data))

    def __str__(self):
        return "\n".join([str(sub) for sub in self])
