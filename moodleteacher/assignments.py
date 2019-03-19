'''
Functionality dealing with Moodle assignments.
'''

import datetime

from .submissions import MoodleSubmissions
from .requests import MoodleRequest
from .courses import MoodleCourse


class MoodleAssignment():
    '''
        A Moodle assignment.
    '''
    duedate = None
    cutoffdate = None
    deadline = None
    id_ = None
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
        self.cutoffdate = datetime.datetime.fromtimestamp(
            raw_json['cutoffdate'])
        if self.duedate < self.cutoffdate:
            self.deadline = self.cutoffdate
        else:
            self.deadline = self.duedate
        self.id_ = raw_json['id']
        self.cmid = raw_json['cmid']
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

    def __init__(self, conn, course_filter=None, assignment_filter=None):
        params = {}
        if course_filter:
            params['courseids'] = course_filter
        response = MoodleRequest(
            conn, 'mod_assign_get_assignments').get(**params).json()
        for course_data in response['courses']:
            course = MoodleCourse.from_raw_json(conn, course_data)
            if (course_filter and course.id_ in course_filter) or not course_filter:
                for ass_data in course_data['assignments']:
                    assignment = MoodleAssignment(conn, course, ass_data)
                    if (assignment_filter and assignment.cmid in assignment_filter) or not assignment_filter:
                        self.append(assignment)
