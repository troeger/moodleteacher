from .requests import MoodleRequest


class MoodleSubmission():
    '''
        A single student submission in Moodle.
    '''
    GRADED = 'graded'
    NOT_GRADED = 'notgraded'

    def __init__(self, conn, assignment, raw_json):
        self.assignment = assignment
        self.conn = conn
        self.raw_json = raw_json
        self.id = raw_json['id']
        self.userid = raw_json['userid']
        self.groupid = raw_json['groupid']
        self.status = raw_json['status']
        self.gradingstatus = raw_json['gradingstatus']
        self.files = []
        self.textfield = None
        for plugin in raw_json['plugins']:
            if plugin['type'] == 'file':
                filelist = plugin['fileareas'][0]['files']
                for f in filelist:
                    self.files.append(f['fileurl'])
            if plugin['type'] == 'onlinetext':
                self.textfield = plugin['editorfields'][0]['text']

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
        if self.is_group_submission:
            user_id = self.get_group_members()[0].id
            applytoall = int(True)
        else:
            user_id = self.user_id
            applytoall = int(False)
        params = {'assignmentid': self.assignment.id,
                  'userid': user_id,
                  'grade': float(grade),
                  'attemptnumber': -1,
                  'addattempt': int(True),
                  'workflowstate': self.GRADED,
                  'applytoall': applytoall,
                  'plugindata[assignfeedbackcomments_editor][text]': str(feedback),
                  # //content format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
                  'plugindata[assignfeedbackcomments_editor][format]': 2
                  }
        MoodleRequest(
            self.conn, 'mod_assign_save_grade').post(params).json()


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
