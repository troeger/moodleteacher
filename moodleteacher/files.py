import mimetypes
import zipfile
import tarfile
from io import BytesIO
import os
import os.path
import re
import requests
import shutil
from tempfile import NamedTemporaryFile

from .exceptions import *

import logging
logger = logging.getLogger('moodleteacher')


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
        An in-memory file representation that was downloaded from Moodle.
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
    name = None                  # File name, without path information
    folder = None                # The MoodeFolder this file belongs to
    size = None
    url = None
    mimetype = None
    encoding = None
    content_type = None
    content = None
    relative_path = ''           # The path on the server, relative to MoodleFolder
    owner = None
    is_binary = None
    is_pdf = False
    is_zip = False
    is_html = False
    is_image = False
    is_tar = False

    def __str__(self):
        return "{0.relative_path}{0.name}".format(self)

    @classmethod
    def from_url(cls, conn, url):
        f = cls()
        f.conn = conn
        f.url = url
        response = requests.get(f.url, params={
                                'token': f.conn.token})
        f.encoding = response.encoding
        try:
            disp = response.headers['content-disposition']
            f.name = re.findall('filename="(.+)"', disp)[0]
        except KeyError:
            f.name = f.url.split('/')[-1]
        f.content_type = response.headers.get('content-type')
        f.content = response.content
        f._analyze_content()
        return f

    @classmethod
    def from_local_data(cls, name, content):
        f = cls()
        f.name = name
        f.content = content
        f._analyze_content()
        return f

    @classmethod
    def from_local_file(cls, fpath):
        name = os.path.basename(fpath)
        with open(fpath, 'rb') as fcontent:
            return cls.from_local_data(name, fcontent.read())

    @property
    def _is_zip_content(self):
        try:
            zipfile.ZipFile(BytesIO(self.content))
            return True
        except Exception:
            return False

    @property
    def _is_tar_content(self):
        try:
            tarfile.open(BytesIO(self.content))
            return True
        except Exception:
            return False

    def _analyze_content(self):
        '''
        Analyzes the content of the file and sets some information bits.
        '''
        assert(self.content)
        # Check for binary file
        self.is_binary = False if isinstance(self.content, str) else True
        # Determine missing content type
        if not self.content_type:
            if self.name.startswith('__MACOSX'):
                self.content_type = 'text/plain'
            elif self._is_zip_content:
                self.content_type = 'application/zip'
                logger.debug("Detected ZIP file content")
            elif self._is_tar_content:
                self.content_type = 'application/tar'
                logger.debug("Detected TAR file content")
            else:
                with NamedTemporaryFile() as tmp:
                    tmp.write(self.content)
                    tmp.flush()
                    self.content_type = mimetypes.guess_type(tmp.name)[0]
                    logger.debug("Detected {0} file content".format(self.content_type))
        # Set convinience flags
        self.is_zip = True if 'application/zip' in self.content_type else False
        self.is_tar = True if self.content_type in self.TAR_CONTENT else False
        self.is_html = True if 'text/html' in self.content_type else False
        self.is_image = True if 'image/' in self.content_type else False
        self.is_pdf = True if 'application/pdf' in self.content_type else False

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

    def unpack_to(self, target_dir):
        '''
        Unpack the content of the submission to the working directory.
        If not file is not an archive, it is directly stored in target_dir
        '''
        assert(self.content)

        dusage = shutil.disk_usage(target_dir)
        if dusage.free < 1024 * 1024 * 50:   # 50 MB
            info_student = "Internal error with the validator. Please contact your course responsible."
            info_tutor = "Error: Execution cancelled, less then 50MB of disk space free on the executor."
            logger.error(info_tutor)
            raise JobException(info_student=info_student, info_tutor=info_tutor)

        dircontent = os.listdir(target_dir)
        logger.debug("Content of %s before unarchiving: %s" %
                     (target_dir, str(dircontent)))

        if self.is_zip:
            input_zip = zipfile.ZipFile(BytesIO(self.content))
            input_zip.extractall(target_dir)
        elif self.is_tar:
            input_tar = tarfile.open(BytesIO(self.content))
            input_tar.extractall(target_dir)
        else:
            logger.debug("Assuming non-archive, copying student submission directly.")
            f = open(target_dir + self.name, 'w+b' if self.is_binary else 'w+')
            f.write(self.content)
            f.close()
