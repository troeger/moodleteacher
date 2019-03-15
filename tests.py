import unittest
import moodleteacher as mt


class TestMoodleFolders(unittest.TestCase):

    def setUp(self):
        self.conn = mt.MoodleConnection(interactive=True)

    def test_folder_list(self):
        mt.MoodleFolders(self.conn)
