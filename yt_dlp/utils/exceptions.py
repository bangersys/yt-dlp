import errno
import sys
import traceback


def bug_reports_message(before=';'):
    from ..update import REPOSITORY

    msg = (f'please report this issue on  https://github.com/{REPOSITORY}/issues?q= , '
           'filling out the appropriate issue template. Confirm you are on the latest version using  yt-dlp -U')

    before = before.rstrip()
    if not before or before.endswith(('.', '!', '?')):
        msg = msg[0].title() + msg[1:]

    return (before + ' ' if before else '') + msg


class YoutubeDLError(Exception):
    """Base exception for YoutubeDL errors."""
    msg = None

    def __init__(self, msg=None):
        if msg is not None:
            self.msg = msg
        elif self.msg is None:
            self.msg = type(self).__name__
        super().__init__(self.msg)


class ExtractorError(YoutubeDLError):
    """Error during info extraction."""

    def __init__(self, msg, tb=None, expected=False, cause=None, video_id=None, ie=None):
        """ tb, if given, is the original traceback (so that it can be printed out).
        If expected is set, this is a normal error message and most likely not a bug in yt-dlp.
        """
        from ..networking.exceptions import network_exceptions
        if sys.exc_info()[0] in network_exceptions:
            expected = True

        self.orig_msg = str(msg)
        self.traceback = tb
        self.expected = expected
        self.cause = cause
        self.video_id = video_id
        self.ie = ie
        self.exc_info = sys.exc_info()  # preserve original exception
        if isinstance(self.exc_info[1], ExtractorError):
            self.exc_info = self.exc_info[1].exc_info
        super().__init__(self.__msg)

    @property
    def __msg(self):
        from ._utils import format_field

        return ''.join((
            format_field(self.ie, None, '[%s] '),
            format_field(self.video_id, None, '%s: '),
            self.orig_msg,
            format_field(self.cause, None, ' (caused by %r)'),
            '' if self.expected else bug_reports_message()))

    def format_traceback(self):
        from ._utils import join_nonempty

        return join_nonempty(
            self.traceback and ''.join(traceback.format_tb(self.traceback)),
            self.cause and ''.join(traceback.format_exception(None, self.cause, self.cause.__traceback__)[1:]),
            delim='\n') or None

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if getattr(self, 'msg', None) and name not in ('msg', 'args'):
            self.msg = self.__msg or type(self).__name__
            self.args = (self.msg, )  # Cannot be property


class UnsupportedError(ExtractorError):
    def __init__(self, url):
        super().__init__(
            f'Unsupported URL: {url}', expected=True)
        self.url = url


class RegexNotFoundError(ExtractorError):
    """Error when a regex didn't match"""
    pass


class GeoRestrictedError(ExtractorError):
    """Geographic restriction Error exception.

    This exception may be thrown when a video is not available from your
    geographic location due to geographic restrictions imposed by a website.
    """

    def __init__(self, msg, countries=None, **kwargs):
        kwargs['expected'] = True
        super().__init__(msg, **kwargs)
        self.countries = countries


class UserNotLive(ExtractorError):
    """Error when a channel/user is not live"""

    def __init__(self, msg=None, **kwargs):
        kwargs['expected'] = True
        super().__init__(msg or 'The channel is not currently live', **kwargs)


class DownloadError(YoutubeDLError):
    """Download Error exception.

    This exception may be thrown by FileDownloader objects if they are not
    configured to continue on errors. They will contain the appropriate
    error message.
    """

    def __init__(self, msg, exc_info=None):
        """ exc_info, if given, is the original exception that caused the trouble (as returned by sys.exc_info()). """
        super().__init__(msg)
        self.exc_info = exc_info


class EntryNotInPlaylist(YoutubeDLError):
    """Entry not in playlist exception.

    This exception will be thrown by YoutubeDL when a requested entry
    is not found in the playlist info_dict
    """
    msg = 'Entry not found in info'


class SameFileError(YoutubeDLError):
    """Same File exception.

    This exception will be thrown by FileDownloader objects if they detect
    multiple files would have to be downloaded to the same file on disk.
    """
    msg = 'Fixed output name but more than one file to download'

    def __init__(self, filename=None):
        if filename is not None:
            self.msg += f': {filename}'
        super().__init__(self.msg)


class PostProcessingError(YoutubeDLError):
    """Post Processing exception.

    This exception may be raised by PostProcessor's .run() method to
    indicate an error in the postprocessing task.
    """


class DownloadCancelled(YoutubeDLError):
    """ Exception raised when the download queue should be interrupted """
    msg = 'The download was cancelled'


class ExistingVideoReached(DownloadCancelled):
    """ --break-on-existing triggered """
    msg = 'Encountered a video that is already in the archive, stopping due to --break-on-existing'


class RejectedVideoReached(DownloadCancelled):
    """ --break-match-filter triggered """
    msg = 'Encountered a video that did not match filter, stopping due to --break-match-filter'


class MaxDownloadsReached(DownloadCancelled):
    """ --max-downloads limit has been reached. """
    msg = 'Maximum number of downloads reached, stopping due to --max-downloads'


class ReExtractInfo(YoutubeDLError):
    """ Video info needs to be re-extracted. """

    def __init__(self, msg, expected=False):
        super().__init__(msg)
        self.expected = expected


class ThrottledDownload(ReExtractInfo):
    """ Download speed below --throttled-rate. """
    msg = 'The download speed is below throttle limit'

    def __init__(self):
        super().__init__(self.msg, expected=False)


class UnavailableVideoError(YoutubeDLError):
    """Unavailable Format exception.

    This exception will be thrown when a video is requested
    in a format that is not available for that video.
    """
    msg = 'Unable to download video'

    def __init__(self, err=None):
        if err is not None:
            self.msg += f': {err}'
        super().__init__(self.msg)


class ContentTooShortError(YoutubeDLError):
    """Content Too Short exception.

    This exception may be raised by FileDownloader objects when a file they
    download is too small for what the server announced first, indicating
    the connection was probably interrupted.
    """

    def __init__(self, downloaded, expected):
        super().__init__(f'Downloaded {downloaded} bytes, expected {expected} bytes')
        # Both in bytes
        self.downloaded = downloaded
        self.expected = expected


class XAttrMetadataError(YoutubeDLError):
    def __init__(self, code=None, msg='Unknown error'):
        super().__init__(msg)
        self.code = code
        self.msg = msg

        # Parsing code and msg
        if (self.code in (errno.ENOSPC, errno.EDQUOT)
                or 'No space left' in self.msg or 'Disk quota exceeded' in self.msg):
            self.reason = 'NO_SPACE'
        elif self.code == errno.E2BIG or 'Argument list too long' in self.msg:
            self.reason = 'VALUE_TOO_LONG'
        else:
            self.reason = 'NOT_SUPPORTED'


class XAttrUnavailableError(YoutubeDLError):
    pass
