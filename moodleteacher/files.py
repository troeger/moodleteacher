import mimetypes
import zipfile
import tarfile
from io import BytesIO
import os
import os.path
import re
import shutil
from tempfile import NamedTemporaryFile

from .exceptions import *
from .requests import BaseRequest

import logging
logger = logging.getLogger('moodleteacher')


class MoodleFolder():
    '''
        A single folder in Moodle. On construction,
        all file information in the folder is also determined,
        but the files themselves are not downloaded.

        TODO: Create constructor from ID only, fetch details with
        separate API call.
    '''

    def __init__(self, conn, course, raw_json):
        self.conn = conn
        self.course = course
        self.id_ = int(raw_json['id'])
        self.name = raw_json['name']
        self.visible = bool(raw_json['visible'])
        self.files = []
        for file_detail in raw_json['contents']:
            f = MoodleFile.from_url(self.conn, file_detail['fileurl'])
            if not f.mime_type:
                f.mime_type = file_detail['mimetype']
            if not f.size:
                f.size = file_detail['filesize']
            if not f.relative_path:
                f.relative_path = file_detail['filepath']
            if not f.time_modified:
                f.time_modified = file_detail['timemodified']
            # Testing showed that raw_json['name'] might contain broken
            # unicode characters, while file_detail['filename'] is rendered
            # correctly.
            if f.name != file_detail['filename']:
                f.name = file_detail['filename']
            f.folder = self
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
                   'application/tar+gzip', 'application/x-gtar', 'application/x-tgz',
                   'application/x-tar']

    def __str__(self):
        result = "{0.relative_path}{0.name}".format(self)
        if self.size:
            result += " ({0.size} Bytes)".format(self)
        return result

    def __init__(self, name, content, conn=None, url=None, encoding=None, content_type=None, mime_type=None, size=None, folder=None, relative_path='', owner=None, time_modified=None):
        self.name = name
        self.content = content
        self.conn = conn
        self.url = url
        self.encoding = encoding
        self.mime_type = mime_type
        self.size = size
        self.folder = folder
        self.relative_path = relative_path
        self.owner = owner
        self.time_modified = time_modified

        # Determine missing content type
        if not content_type:
            if self.name.startswith('__MACOSX'):
                self.content_type = 'text/plain'
            elif self._is_zip_content:
                self.content_type = 'application/zip'
                logger.debug("Detected ZIP file content by probing")
            elif self._is_tar_content:
                self.content_type = 'application/tar'
                logger.debug("Detected TAR file content by probing")
            else:
                with NamedTemporaryFile(suffix=self.name) as tmp:
                    tmp.write(self.content)
                    tmp.flush()
                    self.content_type = mimetypes.guess_type(tmp.name)[0]
                    if self.content_type is None:
                        logger.warn("Unidentifiable content type, declaring it as text.")
                        self.content_type = "application/text"
                    else:
                        logger.debug(
                            "Detected {0} file content by mime guessing".format(self.content_type))
        else:
            self.content_type = content_type

    @classmethod
    def from_url(cls, conn, url, name=None, time_modified=None, mime_type=None):
        # fetch file from url
        response = BaseRequest(conn, url).get_absolute(params={'token': conn.token})

        if not name:
            try:
                disp = response.headers['content-disposition']
                name = re.findall('filename="(.+)"', disp)[0]
            except KeyError:
                name = url.split('/')[-1]

        return cls(name=name,
                   content=response.content,
                   conn=conn,
                   url=url,
                   encoding=response.encoding,
                   time_modified=time_modified,
                   mime_type=mime_type,
                   content_type=response.headers.get('content-type')
                   )

    @classmethod
    def from_local_data(cls, name, content):
        return cls(name=name, content=content)

    @classmethod
    def from_local_file(cls, fpath):
        name = os.path.basename(fpath)
        with open(fpath, 'rb') as fcontent:
            return cls(name=name, content=fcontent.read())

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

    @property
    def is_binary(self):
        return False if isinstance(self.content, str) else True

    @property
    def is_archive(self):
        return self.is_zip or self.is_tar

    @property
    def is_zip(self):
        return True if 'application/zip' in self.content_type else False

    @property
    def is_tar(self):
        return True if self.content_type in self.TAR_CONTENT else False

    @property
    def is_html(self):
        return True if 'text/html' in self.content_type else False

    @property
    def is_image(self):
        return True if 'image/' in self.content_type else False

    @property
    def is_pdf(self):
        return True if 'application/pdf' in self.content_type else False

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

    def _check_disk_space(self, target_dir):
        dusage = shutil.disk_usage(target_dir)
        if dusage.free < 1024 * 1024 * 50:   # 50 MB
            info_student = "Internal error with the validator. Please contact your course responsible."
            info_tutor = "Error: Execution cancelled, less then 50MB of disk space free on the executor."
            logger.error(info_tutor)
            raise JobException(info_student=info_student,
                               info_tutor=info_tutor)

    def save_as(self, target_dir, name, recode=False):
        self._check_disk_space(target_dir)

        if recode:
            # It is tempting to check for the "is_binary=False" condition here, but since the encoding could be
            # anything, the implementation of is_binary() can be only treated as nice guess. Given that,
            # we trust in the caller to know what she does when enabling the recode feature, and just assume
            # from here that we deal with text.
            f = open(target_dir + name, 'w+b')    # encode() returns a byte string to be written to the file
            if self.encoding:
                logger.debug("Recoding text file {0} from {1} to utf-8 ...".format(name, self.encoding))
                try:
                    text = self.content.decode(self.encoding)
                except Exception:
                    # Fallback
                    text = self.content.decode("ISO-8859-1", errors="ignore")
            else:
                logger.warn("Recoding of text file {0} was requested, but the file download has no encoding information. Trying it anway ...".format(name))
                text = self.content.decode("ISO-8859-1", errors="ignore")
            f.write(text.encode("utf-8"))
        else:
            # plain copy
            f = open(target_dir + name, 'w+b' if self.is_binary else 'w+')
            f.write(self.content)
        f.close()

    def unpack_to(self, target_dir, remove_directories, recode=False):
        """Unpack the content of the submission to the working directory.

        If not file is not an archive, it is directly stored in target_dir.
        This directory is expected to be already existent.

        On low disk space, this method refuses to work in order to protect the access to
        log files on the testing machine.

        Recoding is only performed for non-archives, since archive content has no information about
        the original text encoding of its content. For non-archive files, we assume that the encoding
        was set during the download.

        Args:
            remove_directories (boolean): When the student submission is an archive, remove all contained
                                          directories and unpack flat. This makes sense for all but Java code.
                                          When the student submission is not an archive, this flag has no effect.
            recode (boolean):             Recode the submission files to UTF-8 text, to avoid compiler problems.
                                          When the student submission is an archive, this flag has no effect.
        """
        assert(self.content)
        self._check_disk_space(target_dir)

        dircontent = os.listdir(target_dir)
        logger.debug("Content of %s before unarchiving: %s" %
                     (target_dir, str(dircontent)))

        if self.is_zip:
            input_zip = zipfile.ZipFile(BytesIO(self.content))
            if remove_directories:
                logger.debug("Ignoring directories in ZIP archive.")
                infolist = input_zip.infolist()
                for file_in_zip in infolist:
                    if not file_in_zip.filename.endswith('/'):
                        target_name = target_dir + os.sep + \
                            os.path.basename(file_in_zip.filename)
                        logger.debug("Writing {0} to {1}".format(
                            file_in_zip.filename, target_name))
                        with open(target_name, "wb") as target:
                            target.write(input_zip.read(file_in_zip))
                    else:
                        logger.debug("Ignoring ZIP entry '{0}'".format(
                            file_in_zip.filename))
            else:
                logger.debug("Keeping directories from ZIP archive.")
                input_zip.extractall(target_dir)
        elif self.is_tar:
            input_tar = tarfile.open(fileobj=BytesIO(self.content))
            if remove_directories:
                logger.debug("Ignoring directories in TAR archive.")
                infolist = input_tar.getmembers()
                for file_in_tar in infolist:
                    if file_in_tar.isfile():
                        target_name = target_dir + os.sep + \
                            os.path.basename(file_in_tar.name)
                        logger.debug("Writing {0} to {1}".format(
                            file_in_tar.name, target_name))
                        with open(target_name, "wb") as target:
                            target.write(input_tar.extractfile(
                                file_in_tar).read())
                    else:
                        logger.debug(
                            "Ignoring TAR entry '{0}'".format(file_in_tar.name))
            else:
                logger.debug("Keeping directories from TAR archive.")
                input_tar.extractall(target_dir)
        else:
            logger.debug("Assuming non-archive, copying directly.")
            self.save_as(target_dir, self.name, recode)

        dircontent = os.listdir(target_dir)
        logger.debug("Content of %s after unarchiving: %s" %
                     (target_dir, str(dircontent)))
