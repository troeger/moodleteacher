import subprocess
import mimetypes
from zipfile import ZipFile
from io import BytesIO
import os
import os.path
import re
import tempfile
import requests

from .requests import MoodleRequest


class MoodleFolder():
    '''
        A single folder in Moodle. On construction,
        all file information in the folder is also determined,
        but the files themselves are not downloaded.
    '''

    def __init__(self, conn, course, raw_json):
        self.conn = conn
        self.course = course
        self.id = raw_json['id']
        self.name = raw_json['name']
        self.visible = bool(raw_json['visible'])
        self.files = []
        for file_detail in raw_json['contents']:
            f = MoodleFile()
            f.conn = self.conn
            f.name = file_detail['filename']
            f.folder = self
            f.size = file_detail['filesize']
            f.url = file_detail['fileurl']
            f.mimetype = file_detail['mimetype']
            f.relative_path = file_detail['filepath']
            f.owner = self.course.get_user(file_detail['userid'])
            self.files.append(f)

    def __str__(self):
        return "{0.name} ({1} files)".format(self, len(self.files))


class MoodleFile():
    '''
        A file stored in Moodle.
    '''
    # Content types we don't know how to deal with in the preview
    UNKNOWN_CONTENT = ['application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                       'application/vnd.oasis.opendocument.text']
    # Content types that come as byte stream download, and not as text with an encoding
    BINARY_CONTENT = ['application/pdf', 'application/x-sh',
                      'application/zip'] + UNKNOWN_CONTENT
    # Different content types for a TGZ file
    TAR_CONTENT = ['application/x-gzip', 'application/gzip', 'application/tar',
                   'application/tar+gzip', 'application/x-gtar', 'application/x-tgz']

    conn = None
    name = None
    folder = None
    size = None
    url = None
    mimetype = None
    encoding = None
    content_type = None
    content = None
    relative_path = ''
    owner = None
    is_binary = None
    is_pdf = False
    is_zip = False
    is_html = False
    is_image = False
    is_tar = False

    def __str__(self):
        return "{0.relative_path}{0.name}".format(self)

    def download(self):
        '''
        Download the file content and stores in in self.content.
        Expects self.url to be set.

        The method fills self.name, self.content_type and
        self.encoding with the determined information.
        If self.name is already set, it will not be changed.
        '''
        assert(self.conn)
        assert(self.url)
        response = requests.get(self.url, params={
                                'token': self.conn.token})
        self.encoding = response.encoding
        if not self.name:
            try:
                disp = response.headers['content-disposition']
                self.name = re.findall('filename="(.+)"', disp)[0]
            except KeyError:
                self.name = self.url.split('/')[-1]
        self.content_type = response.headers.get('content-type')
        self.content = response.content
        self.analyze_content()

    def analyze_content(self):
        '''
        Analyzes the content of the file and sets some information bits.
        Expects self.content to be set.
        '''
        assert(self.content)
        self.is_binary = False if isinstance(self.content, str) else True
        if self.content_type:
            self.is_pdf = True if 'application/pdf' in self.content_type else False
            self.is_zip = True if 'application/zip' in self.content_type else False
            self.is_html = True if 'text/html' in self.content_type else False
            self.is_image = True if 'image/' in self.content_type else False
            self.is_tar = True if self.content_type in self.TAR_CONTENT else False

    def as_text(self):
        '''
        Return the content of the file as printable text.
        '''
        assert(self.content)
        if self.is_binary:
            if self.encoding:
                return self.content.decode(self.encoding)
            else:
                # Fallback
                return self.content.decode("ISO-8859-1", errors="ignore")
        else:
            return self.content


class MoodleSubmissionFile(MoodleFile):
    '''
        A single student submission file in Moodle.
    '''
    SHELL = ['/bin/bash', ]

    def __init__(self, *args, **kwargs):
        '''
        Construct a new MoodleSubmissionFile object.

        Variant 1: Manual construction, provide 'filename', 'content' and 'content_type'
        Variant 2: Construction from download, provide 'conn' and 'url'
        '''
        if 'filename' in kwargs and 'content' in kwargs:
            # Pseudo file
            self.name = kwargs['filename']
            self.content = kwargs['content']
            if 'content_type' in kwargs:
                self.content_type = kwargs['content_type']
            else:
                # Special treatement of meta-files
                if self.name.startswith('__MACOSX'):
                    self.content_type = 'text/plain'
                else:
                    self.content_type = mimetypes.guess_type(self.filename)[0]
        elif 'conn' in kwargs or 'url' in kwargs:
            self.conn = kwargs['conn']
            self.url = kwargs['url']
            self.download()
        else:
            raise ValueError

    def run_shellscript_local(self, args=[]):
        assert(self.content)
        with tempfile.NamedTemporaryFile(mode='w+b' if self.is_binary else 'w+') as disk_file:
            disk_file.write(self.content)
            disk_file.flush()
            return subprocess.run([*self.SHELL, disk_file.name, *args], stderr=subprocess.STDOUT)

    def compile_with(self, cmd):
        assert(self.content)
        with tempfile.TemporaryDirectory() as d:
            f = open(d + os.sep + self.filename, mode="w")
            f.write(self.content)
            f.close()
            compile_output = subprocess.run([*cmd.split(' '), self.filename], cwd=d, stderr=subprocess.STDOUT)
            return

    @staticmethod
    def from_urls(conn, file_urls):
        '''
        Create a list of MoodleSubmissionFile objects from a list of URLs.

        ZIP or TAR.GZ archives are also downloaded and automatically uncompressed.
        In such a case, a single file URL may still lead to an array of MoodleSubmissionFile
        objects being returned.
        '''
        obj_list = []
        for file_url in file_urls:
            f = MoodleSubmissionFile(conn=conn, url=file_url)
            if f.is_zip:
                input_zip = ZipFile(BytesIO(f.content))
                arch_files = [
                    info.filename for info in input_zip.infolist() if not info.is_dir()]
                for fname in arch_files:
                    data = input_zip.read(fname)
                    sub_f = MoodleSubmissionFile(
                        filename=fname, content=data)
                    sub_f.analyze_content()
                    obj_list.append(sub_f)
            elif f.is_tar:
                input_tar = tarfile.open(BytesIO(f.content))
                arch_files = [info for info in input_tar.getmembers()]
                for info in arch_files:
                    data = input_tar.extractfile(info)
                    sub_f = MoodleSubmissionFile(
                        filename=info.name, content=data)
                    sub_f.analyze_content()
                    obj_list.append(sub_f)
            else:
                obj_list.append(f)
        return obj_list

    def run_shellscript_remote(self, user_name, host, target_path, args=[]):
        '''
        Copy the file to a remote SCP host and run it. Ignores authentication.
        '''
        assert(self.content)
        with tempfile.NamedTemporaryFile(mode='w+b' if self.is_binary else 'w+') as disk_file:
            disk_file.write(self.content)
            disk_file.flush()
            subprocess.run(['scp', disk_file.name, '{0}@{1}:{2}/'.format(
                user_name, host, target_path)], stderr=subprocess.STDOUT)
            return subprocess.run(['ssh',
                                   '{0}@{1}'.format(user_name, host),
                                   ' '.join([*self.SHELL, target_path + os.sep + os.path.basename(disk_file.name), *args])
                                   ], stderr=subprocess.STDOUT)

    def __str__(self):
        return "{0.filename} ({0.content_type})".format(self)
