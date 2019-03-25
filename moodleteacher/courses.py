from collections import defaultdict

from .requests import MoodleRequest
from .users import MoodleUser, MoodleGroup
from .files import MoodleFolder
from .grades import MoodleGradeItem

import logging
logger = logging.getLogger('moodleteacher')


class MoodleCourse():
    '''
        A single Moodle course.
    '''
    assignments = []
    id_ = None
    fullname = None
    shortname = None
    can_grade = None
    users = {}          # key is user id, value is MoodleUser object
    groups = {}         # key is group id, value is MoodleGroup object
    group_members = defaultdict(set)  # key is group ID, value id user ID

    @classmethod
    def from_raw_json(cls, conn, raw_json):
        '''
        Create a MoodleCourse object from raw JSON information.
        '''
        return cls(conn=conn, course_id=raw_json['id'],
                   fullname=raw_json['fullname'],
                   shortname=raw_json['shortname'])

    @classmethod
    def from_course_id(cls, conn, course_id):
        '''
        Create a MoodleCourse object just from a course ID.

        TODO: Determine missing information pieces with an API call.
        '''
        return cls(conn=conn, course_id=course_id,
                   fullname="",
                   shortname="")

    def __init__(self, conn, course_id, fullname="", shortname=""):
        self.conn = conn
        self.id_ = course_id
        self.fullname = fullname
        self.shortname = shortname
        self.get_admin_options(conn)
        # fetch list of users and groups in this course
        params = {'courseid': self.id_}
        raw_json = MoodleRequest(
            conn, 'core_enrol_get_enrolled_users').post(params).json()
        for raw_json_user in raw_json:
            moodle_user = MoodleUser.from_json(raw_json_user)
            # Django get_or_create ... in ugly.
            self.users[moodle_user.id_] = moodle_user
            if 'groups' in raw_json_user.keys():
                for raw_json_group in raw_json_user['groups']:
                    moodle_group = MoodleGroup.from_json(self, raw_json_group)
                    self.groups[moodle_group.id_] = moodle_group
                    self.group_members[moodle_group.id_].add(moodle_user.id_)

    def get_group(self, group_id):
        '''
        Returns MoodleGroup object for this user id,
        or None if not known.
        '''
        if group_id in self.groups.keys():
            return self.groups[group_id]
        else:
            return None

    def get_user(self, user_id):
        '''
        Returns MoodleUser object for this user id,
        or None if not known.
        '''
        if user_id in self.users.keys():
            return self.users[user_id]
        else:
            return None

    def get_group_members(self, group_id):
        return [self.users[user_id] for user_id in self.group_members[group_id]]

    def get_user_grades(self, user_id):
        '''
            Fetch grade table for this user, or all users, in the given course.
        '''
        params = {'courseid': self.id_, 'userid': user_id}
        response = MoodleRequest(
            self.conn, 'gradereport_user_get_grade_items').post(params).json()
        grade_data = response['usergrades'][0]
        assert(grade_data['courseid'] == self.id_)
        assert(grade_data['userid'] == user_id)
        result = []
        for gradeitem in grade_data['gradeitems']:
            if 'cmid' in gradeitem:
                # Only consider real assignments
                result.append(MoodleGradeItem.from_raw_json(gradeitem))
        return result

    def get_folders(self):
        '''
        Determine folders that are part of the course.

        Returns list of MoodleFolder objects.
        '''
        result = []
        params = {'courseid': self.id_}
        raw_json = MoodleRequest(
            self.conn, 'core_course_get_contents').post(params).json()
        for section in raw_json:
            for module in section['modules']:
                if module['modname'] == 'folder':
                    logger.debug("Found folder: {name} - ID {id}".format(**module))
                    result.append(MoodleFolder(self.conn, self, module))
        return result

    def __str__(self):
        return self.fullname if self.fullname else self.shortname if self.shortname else str(self.id_)

    def get_admin_options(self, conn):
        params = {'courseids[0]': self.id_}
        response = MoodleRequest(
            conn, 'core_course_get_user_administration_options').post(params).json()
        if 'courses' in response:
            for option in response['courses'][0]['options']:
                if option['name'] == 'gradebook':
                    if option['available'] is True:
                        self.can_grade = True
                    else:
                        self.can_grade = False
        else:
            if self.conn.is_fake:
                self.can_grade = True
            else:
                self.can_grade = False

    def assignments(self):
        from .assignments import MoodleAssignments
        return MoodleAssignments(self.conn, course_filter=[self.id_, ])
