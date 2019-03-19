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

    @classmethod
    def from_raw_json(cls, conn, course, raw_json):
        '''
        Create a MoodleAssignment object from raw JSON information.
        '''
        o = cls(conn=conn, course=course, assignment_id=raw_json['id'])
        o.duedate = datetime.datetime.fromtimestamp(raw_json['duedate'])
        o.cutoffdate = datetime.datetime.fromtimestamp(
            raw_json['cutoffdate'])
        if o.duedate < o.cutoffdate:
            o.deadline = o.cutoffdate
        else:
            o.deadline = o.duedate
        o.cmid = raw_json['cmid']
        o.name = raw_json['name']
        o.allows_feedback_comment = False
        for config in raw_json['configs']:
            if config['plugin'] == 'comments' and \
               config['subtype'] == 'assignfeedback' and \
               config['name'] == 'enabled' and \
               config['value'] == '1':
                o.allows_feedback_comment = True
        return o

    @classmethod
    def from_assignment_id(cls, conn, course, assignment_id):
        '''
        Create a MoodleAssignment object just from a course ID.

        TODO: Determine missing information pieces with an API call.
        '''
        return cls(conn=conn, course=course, assignment_id=assignment_id)

    def __init__(self, conn, course, assignment_id):
        self.conn = conn
        self.course = course
        self.id_ = assignment_id

    def __str__(self):
        if self.name:
            return("{0.name} (Fällig: {0.deadline})".format(self))
        else:
            return self.id_

    def deadline_over(self):
        return datetime.datetime.now() > self.deadline

    def submissions(self):
        return MoodleSubmissions.from_assignment(self)


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
                    assignment = MoodleAssignment.from_raw_json(conn, course, ass_data)
                    if (assignment_filter and assignment.cmid in assignment_filter) or not assignment_filter:
                        self.append(assignment)
