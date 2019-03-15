import subprocess
import mimetypes
from zipfile import ZipFile
from io import BytesIO
import os
import os.path
import re
import tempfile


from .requests import MoodleRequest


class MoodleFolder():
    '''
        A single folder in Moodle.
    '''

    def __init__(self, conn, course, raw_json):
        self.conn = conn
        self.course = course
        self.id = raw_json['id']
        self.name = raw_json['name']
        self.visible = bool(raw_json['visible'])
        self.files = []
        for file_detail in raw_json['contents']:
            f = MoodleFile(self.conn, raw_json['filename'])
            f.folder = self
            f.size = raw_json['filesize']
            f.url = raw_json['fileurl']
            f.mimetype = raw_json['mimetype']
            f.relative_path = raw_json['filepath']
            f.owner = self.course.get_user(raw_json['userid'])
            self.files.append(f)

    def __str__(self):
        return "{0.name} ({1} files)".format(self, len(self.files))


class MoodleFile(list):
    '''
        A generic Moodle file.
    '''
    conn = None
    name = None
    folder = None
    size = None
    url = None
    mimetype = None
    encoding = None
    content_type = None
    relative_path = ''
    owner = None

    def __init__(self, conn, name):
        self.conn = conn
        self.name = name

    def __str__(self):
        return "{0.filepath}{0.filename}".format(self)

    def download(self):
        '''
        Download the file content and stores in in self.content.
        Expects self.url to be set.

        The method fills self.name, self.content_type and 
        self.encoding with the determined information.
        If self.name is already set, it will not be changed.
        '''
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




class MoodleSubmissionFile():
    '''
        A single student submission file in Moodle.

        TODO: Migrate generic functionality from here to MoodleFile.
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

    # Shell to suer for execution
    SHELL = ['/bin/bash', ]

    encoding = None
    filename = None
    content_type = None
    content = None
    is_binary = None
    is_pdf = False
    is_zip = False
    is_html = False
    is_image = False
    is_tar = False

    def __init__(self, *args, **kwargs):
        '''
        Construct a new MoodleSubmissionFile object.

        Variant 1: Manual construction, provide 'filename', 'content' and 'content_type'
        Variant 2: Construction from download, provide 'conn' and 'url'
        '''
        if 'filename' in kwargs and 'content' in kwargs:
            # Pseudo file
            self.filename = kwargs['filename']
            self.content = kwargs['content']
            if 'content_type' in kwargs:
                self.content_type = kwargs['content_type']
            else:
                # Special treatement of meta-files
                if self.filename.startswith('__MACOSX'):
                    self.content_type = 'text/plain'
                else:
                    self.content_type = mimetypes.guess_type(self.filename)[0]
        elif 'conn' in kwargs or 'url' in kwargs:
            response = requests.get(kwargs['url'], params={
                                    'token': kwargs['conn'].token})
            self.encoding = response.encoding
            try:
                disp = response.headers['content-disposition']
                self.filename = re.findall('filename="(.+)"', disp)[0]
            except KeyError:
                self.filename = kwargs['url'].split('/')[-1]
            self.content_type = response.headers.get('content-type')
            self.content = response.content
        else:
            raise ValueError
        self.is_binary = False if isinstance(self.content, str) else True
        if self.content_type:
            self.is_pdf = True if 'application/pdf' in self.content_type else False
            self.is_zip = True if 'application/zip' in self.content_type else False
            self.is_html = True if 'text/html' in self.content_type else False
            self.is_image = True if 'image/' in self.content_type else False
            self.is_tar = True if self.content_type in self.TAR_CONTENT else False

    def run_shellscript_local(self, args=[]):
        with tempfile.NamedTemporaryFile(mode='w+b' if self.is_binary else 'w+') as disk_file:
            disk_file.write(self.content)
            disk_file.flush()
            return subprocess.run([*self.SHELL, disk_file.name, *args], stderr=subprocess.STDOUT)

    def compile_with(self, cmd):
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

        URLs for ZIP or TAR.GZ archives are also downloaded and automatically uncompressed.
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
                    obj_list.append(sub_f)
            elif f.is_tar:
                input_tar = tarfile.open(BytesIO(f.content))
                arch_files = [info for info in input_tar.getmembers()]
                for info in arch_files:
                    data = input_tar.extractfile(info)
                    sub_f = MoodleSubmissionFile(
                        filename=info.name, content=data)
                    obj_list.append(sub_f)
            else:
                obj_list.append(f)
        return obj_list

    def run_shellscript_remote(self, user_name, host, target_path, args=[]):
        '''
            Copy the file to a remote SCP host and run it. Ignores authentication.
        '''
        with tempfile.NamedTemporaryFile(mode='w+b' if self.is_binary else 'w+') as disk_file:
            disk_file.write(self.content)
            disk_file.flush()
            subprocess.run(['scp', disk_file.name, '{0}@{1}:{2}/'.format(
                user_name, host, target_path)], stderr=subprocess.STDOUT)
            return subprocess.run(['ssh',
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
