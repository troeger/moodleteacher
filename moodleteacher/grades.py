import logging
logger = logging.getLogger('moodleteacher')


class MoodleGradeItem():
    '''
        A single Moodle grade.
    '''

    def __init__(self, grade_id, item_name, item_cmid, gradeformatted):
        self.id_ = grade_id
        self.item_name = item_name
        self.item_cmid = item_cmid
        self.gradeformatted = gradeformatted

    @classmethod
    def from_raw_json(cls, raw_json):
        return cls(grade_id=raw_json['id'],
                   item_name=raw_json['itemname'],
                   item_cmid=raw_json['cmid'],
                   gradeformatted=raw_json['gradeformatted'])

    def __str__(self):
        return "{0.item_name}: {0.gradeformatted}".format(self)
