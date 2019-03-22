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
    def __init__(self, course, assignment_id, course_module_id=None, duedate=None, cutoffdate=None, deadline=None, name=None, allows_feedback_comment=None):
        self.conn = course.conn
        self.course = course
        self.id_ = assignment_id
        self.cmid = course_module_id
        self.duedate = duedate
        self.cutoffdate = cutoffdate
        self.deadline = deadline
        self.name = name
        self.allows_feedback_comment = allows_feedback_comment

    @classmethod
    def from_raw_json(cls, course, raw_json):
        '''
        Create a MoodleAssignment object from raw JSON information.
        '''
        duedate = datetime.datetime.fromtimestamp(raw_json['duedate'])
        cutoffdate = datetime.datetime.fromtimestamp(raw_json['cutoffdate'])
        allows_feedback_comment = False
        for config in raw_json['configs']:
            if config['plugin'] == 'comments' and \
               config['subtype'] == 'assignfeedback' and \
               config['name'] == 'enabled' and \
               config['value'] == '1':
                allows_feedback_comment = True

        return cls(course=course,
                   assignment_id=raw_json['id'],
                   course_module_id=raw_json['cmid'],
                   duedate=duedate,
                   cutoffdate=cutoffdate,
                   deadline=cutoffdate if duedate < cutoffdate else duedate,
                   name=raw_json['name'],
                   allows_feedback_comment=allows_feedback_comment)

    @classmethod
    def from_assignment_id(cls, course, assignment_id):
        '''
        Create a MoodleAssignment object just from an assignment ID.
        '''
        # This approach is overkill, but
        # there seems to be no API call to fetch single assignment
        # detail information.
        assignments = course.assignments()
        for assignment in assignments:
            if assignment.id_ == assignment_id:
                return assignment
        return None

    @classmethod
    def from_course_module_id(cls, course, course_module_id):
        '''
        Create a MoodleAssignment object just from a course module ID.
        '''
        params = {}
        params['cmid'] = course_module_id
        response = MoodleRequest(
            course.conn, 'core_course_get_course_module').get(**params).json()
        if response['cm']['modname'] == 'assign':
            # Determine missing information.
            # This approach is overkill, but
            # there seems to be no API call to fetch single assignment
            # detail information.
            assignments = course.assignments()
            for assignment in assignments:
                if assignment.id_ == response['cm']['instance']:
                    return assignment
        return None

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
        if 'courses' in response:
            for course_data in response['courses']:
                course = MoodleCourse.from_raw_json(conn, course_data)
                if (course_filter and course.id_ in course_filter) or not course_filter:
                    for ass_data in course_data['assignments']:
                        assignment = MoodleAssignment.from_raw_json(course, ass_data)
                        if (assignment_filter and assignment.cmid in assignment_filter) or not assignment_filter:
                            self.append(assignment)
