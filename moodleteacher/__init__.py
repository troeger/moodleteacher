import datetime
import tempfile
import subprocess
import re
import os
import os.path
import pickle
import logging

import requests

class MoodleConnection():
    '''
        A connection to a Moodle installation.
    '''
    token = None
    ws_url = None
    ws_params = {}
    moodle_host = None

    def __init__(self, moodle_host=None, token=None, interactive=False):
        '''
            Establishes a connection to a Moodle installation.

            Parameters:
                moodle_host: The base URL of the Moodle installation.
                token: The client security token for the user.
                interactive: Prompt user for parameters, if needed.
        '''
        if not moodle_host and not token:
            try:
                with open(os.path.expanduser("~/.moodleteacher"),"rb") as f:
                    moodle_host, token = pickle.load(f)
            except FileNotFoundError:
                if not interactive:
                    raise AttributeError("Please provide moodle_host + token, or set interactive=True")
                else:
                    print("Seems like this your first connection attempt ...")
                    moodle_host = input("URL of the Moodle host: ")
                    token = input("Moodle web service client security token: ")
                    print("I will store these credentials in ~/.moodleteacher for the next time.")
                    with open(os.path.expanduser("~/.moodleteacher"),"xb") as f:
                        pickle.dump([moodle_host, token], f)
        self.token = token
        self.moodle_host = moodle_host
        self.ws_params['wstoken'] = token
        self.ws_params['moodlewsrestformat'] = 'json'
        self.ws_url = moodle_host + "/webservice/rest/server.php"

    def __str__(self):
        return "Connection to " + self.moodle_host

class MoodleRequest():
    '''
        A Moodle web service request.
    '''
    def __init__(self, conn, funcname):
        '''
            Prepares a Moodle web service request.

            Parameters:
                conn: The MoodleConnection object.
                funcname: The name of the Moodle web service function.
        '''
        self.conn = conn
        self.ws_params = conn.ws_params
        self.ws_params['wsfunction'] = funcname

    def get(self):
        '''
            Perform a GET request to the Moodle web service.
        '''
        logging.debug("Performing web service GET call for " + self.ws_params['wsfunction'])
        result = requests.get(self.conn.ws_url, params=self.ws_params)
        logging.debug("Result: " + str(result))
        result.raise_for_status()
        return result

    def post(self, post_params):
        '''
            Perform a POST request to the Moodle web service with the given parameters.
        '''
        post_data = {**self.ws_params, **post_params}
        logging.debug("Performing web service POST call for " + self.ws_params['wsfunction'])
        result = requests.post(self.conn.ws_url, params=post_data)
        logging.debug("Result: " + str(result))
        result.raise_for_status()
        return result

class MoodleUser():
    '''
        A Moodle user account.
    '''
    fullname = None
    email = None

    def __init__(self, conn, user_id):
        '''
            Fetch information about a user, based in the user id.

            Parameters:
                conn: The MoodleConnection object.
                user_id: The numerical user id.
        '''
        params = {'field': 'id', 'values[0]': str(user_id)}
        response = MoodleRequest(conn, 'core_user_get_users_by_field').post(params).json()
        assert(response[0]['id'] == user_id)
        self.fullname = response[0]['fullname']
        self.email = response[0]['email']

class MoodleAssignment():
    '''
        A Moodle assignment.
    '''
    duedate = None
    cutoffdate = None
    deadline = None
    id = None
    name = None
    submissions = None
    allows_feedback_comment = None
    course = None

    def __init__(self, conn, course, raw_json):
        '''
            Parse information about a Moodle assignment, including the list
            of submissions for this assignment.

            Parameters:
                conn: The MoodleConnection object.
                raw_json: The JSON information about the assignment.
        '''
        self.conn = conn
        self.course = course
        self.duedate = datetime.datetime.fromtimestamp(raw_json['duedate'])
        self.cutoffdate = datetime.datetime.fromtimestamp(raw_json['cutoffdate'])
        if self.duedate < self.cutoffdate:
            self.deadline = self.cutoffdate
        else:
            self.deadline = self.duedate
        self.id = raw_json['id']
        self.name = raw_json['name']
        self.allows_feedback_comment = False
        for config in raw_json['configs']:
            if config['plugin'] == 'comments' and \
               config['subtype'] == 'assignfeedback' and \
               config['name'] == 'enabled' and \
               config['value'] == '1':
                self.allows_feedback_comment = True

    def __str__(self):
        return("{0.name} (Fällig: {0.deadline})".format(self))

    def deadline_over(self):
        return datetime.datetime.now() > self.deadline

    def submissions(self):
        return MoodleSubmissions(self.conn, self)

class MoodleAssignments(list):
    '''
        A list of MoodleAssignment instances.
    '''
    def __init__(self, conn, course_filter=None):
        response = MoodleRequest(conn, 'mod_assign_get_assignments').get().json()
        for course_data in response['courses']:
            course = MoodleCourse(conn, course_data)
            if (course_filter and course.id in course_filter) or not course_filter:
                for ass_data in course_data['assignments']:
                    assignment = MoodleAssignment(conn, course, ass_data)
                    self.append(assignment)

class MoodleSubmissionFile():
    '''
        A single student submission file in Moodle.
    '''
    # Content types we don't know how to deal with in the preview
    UNKNOWN_CONTENT = ['application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                       'application/vnd.oasis.opendocument.text']
    # Content types that come as byte stream download, and not as text with an encoding
    BINARY_CONTENT  = ['application/pdf', 'application/x-sh', 'application/zip'] + UNKNOWN_CONTENT
    # Shell to suer for execution
    SHELL = ['/bin/bash',]

    encoding = None
    filename = None
    content_type = None
    content = None
    is_binary = None
    is_pdf = False
    is_zip = False
    is_html = False
    is_image = False

    def __init__(self, *args, **kwargs):
        if 'filename' in kwargs and 'content' in kwargs and 'content_type' in kwargs:
            # Pseudo file
            self.filename = kwargs['filename']
            self.content = kwargs['content']
            self.content_type = kwargs['content_type']
        elif 'conn' in kwargs or 'url' in kwargs:
            response = requests.get(kwargs['url'], params={'token': kwargs['conn'].token})
            self.encoding = response.encoding
            disp = response.headers['content-disposition']
            self.filename = re.findall('filename="(.+)"', disp)[0]
            self.content_type = response.headers.get('content-type')
            if self.content_type in self.BINARY_CONTENT:
                self.content = response.content
            else:
                self.content = response.text
        self.is_binary = False if isinstance(self.content, str) else True
        if self.content_type:
            self.is_pdf = True if 'application/pdf' in self.content_type else False
            self.is_zip = True if 'application/zip' in self.content_type else False
            self.is_html = True if 'text/html' in self.content_type else False
            self.is_image = True if 'image/' in self.content_type else False

    def run_shellscript_local(self, args=[]):
        with tempfile.NamedTemporaryFile(mode='w+b' if self.is_binary else 'w+') as disk_file:
            disk_file.write(self.content)
            disk_file.flush()
            return subprocess.run([*self.SHELL, disk_file.name, *args], stderr=subprocess.STDOUT)

    def compile_with(self, cmd):
        with tempfile.TemporaryDirectory() as d:
            f=open(d + os.sep + self.filename, mode="w")
            f.write(self.content)
            f.close()
            compile_output = subprocess.run([*cmd.split(' '), self.filename], cwd=d, stderr=subprocess.STDOUT)
            return 

    def run_shellscript_remote(self, user_name, host, target_path, args=[]):
        '''
            Copy the file to a remote SCP host and run it. Ignores authentication.
        '''
        with tempfile.NamedTemporaryFile(mode='w+b' if self.is_binary else 'w+') as disk_file:
            disk_file.write(self.content)
            disk_file.flush()
            subprocess.run(['scp', disk_file.name, '{0}@{1}:{2}/'.format(user_name, host, target_path)], stderr=subprocess.STDOUT)
            return subprocess.run([ 'ssh', 
                                    '{0}@{1}'.format(user_name, host),
                                    ' '.join([*self.SHELL, target_path + os.sep + os.path.basename(disk_file.name), *args])
                                   ], stderr=subprocess.STDOUT)

    def as_text(self):
        if self.is_binary:
            if self.encoding:
                return self.content.decode(self.encoding)
            else:
                # No information from web server, final fallback.
                return self.content.decode("ISO-8859-1", errors="ignore")
        else:
            return self.content

    def __str__(self):
        return "{0.filename} ({0.content_type})".format(self)

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
        text = "Abgabe {0.id} durch Nutzer {0.userid} ({0.gradingstatus}), {1} Dateien, ".format(self, num_files)
        if self.textfield:
            text += "mit Text"
        else:
            text += "ohne Text"
        return(text)

    def is_empty(self):
        return len(self.files) == 0 and not self.textfield

    def save_grade(self, grade, feedback=""):
        # You can only give text feedback if your assignment is configured accordingly
        assert(feedback is "" or self.assignment.allows_feedback_comment)
        params = {'assignmentid': self.assignment.id, 
                  'userid': self.userid,
                  'grade': float(grade),
                  'attemptnumber': -1,
                  'addattempt': int(True),
                  'workflowstate': 'graded',
                  'applytoall': int(True),
                  'plugindata[assignfeedbackcomments_editor][text]': str(feedback),
                  # //content format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
                  'plugindata[assignfeedbackcomments_editor][format]': 2
                  }
        response = MoodleRequest(self.conn, 'mod_assign_save_grade').post(params).json()

class MoodleSubmissions(list):
    '''
        A list of MoodleSubmission instances.
    '''
    def __init__(self, conn, assignment):
        params = {'assignmentids[0]': assignment.id}
        response = MoodleRequest(conn, 'mod_assign_get_submissions').post(params).json()
        for response_assignment in response['assignments']:
            assert(response_assignment['assignmentid'] == assignment.id)
            for subm_data in response_assignment['submissions']:
                self.append(MoodleSubmission(conn, assignment, subm_data))

class MoodleCourse():
    '''
        A single Moodle course.
    '''
    assignments = []
    id = None
    fullname = None
    shortname = None
    can_grade = None

    def __init__(self, conn, raw_json):
        self.id = raw_json['id']
        self.fullname = raw_json['fullname']
        self.shortname = raw_json['shortname']
        self.get_admin_options(conn)

    def __str__(self):
        return(self.fullname)

    def get_admin_options(self, conn):
        params = {'courseids[0]': self.id}
        response = MoodleRequest(conn, 'core_course_get_user_administration_options').post(params).json()
        for option in response['courses'][0]['options']:
            if option['name'] == 'gradebook':
                if option['available'] == True:
                    self.can_grade = True
                else:
                    self.can_grade = False

