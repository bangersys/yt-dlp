import collections
import contextlib
import errno
import functools
import io
import operator
import os
import re
import shlex
import subprocess
import sys
import time
import unicodedata

from .version import _get_exe_version_output, detect_exe_version

from ..compat import compat_expanduser
from ..globals import WINDOWS_VT_MODE
from .constants import NUMBER_RE, MEDIA_EXTENSIONS
from .formatting import ACCENT_CHARS, write_string, variadic
from .json import NO_DEFAULT
from .math import lookup_unit_table


def sanitize_open(filename, open_mode):
    """Try to open the given filename, and slightly tweak it if this fails.

    Attempts to open the given filename. If this fails, it tries to change
    the filename slightly, step by step, until it's either able to open it
    or it fails and raises a final exception, like the standard open()
    function.

    It returns the tuple (stream, definitive_file_name).
    """
    if filename == '-':
        if sys.platform == 'win32':
            import msvcrt

            # stdout may be any IO stream, e.g. when using contextlib.redirect_stdout
            with contextlib.suppress(io.UnsupportedOperation):
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        return (sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else sys.stdout, filename)

    for attempt in range(2):
        try:
            try:
                if sys.platform == 'win32':
                    # FIXME: An exclusive lock also locks the file from being read.
                    # Since windows locks are mandatory, don't lock the file on windows (for now).
                    # Ref: https://github.com/yt-dlp/yt-dlp/issues/3124
                    raise LockingUnsupportedError
                stream = locked_file(filename, open_mode, block=False).__enter__()
            except OSError:
                stream = open(filename, open_mode)
            return stream, filename
        except OSError as err:
            if attempt or err.errno in (errno.EACCES,):
                raise
            old_filename, filename = filename, sanitize_path(filename)
            if old_filename == filename:
                raise


def sanitize_filename(s, restricted=False, is_id=NO_DEFAULT):
    """Sanitizes a string so it could be used as part of a filename.
    @param restricted   Use a stricter subset of allowed characters
    @param is_id        Whether this is an ID that should be kept unchanged if possible.
                        If unset, yt-dlp's new sanitization rules are in effect
    """
    if s == '':
        return ''

    def replace_insane(char):
        if restricted and char in ACCENT_CHARS:
            return ACCENT_CHARS[char]
        elif not restricted and char == '\n':
            return '\0 '
        elif is_id is NO_DEFAULT and not restricted and char in '"*:<>?|/\\':
            # Replace with their full-width unicode counterparts
            return {'/': '\u29F8', '\\': '\u29f9'}.get(char, chr(ord(char) + 0xfee0))
        elif char == '?' or ord(char) < 32 or ord(char) == 127:
            return ''
        elif char == '"':
            return '' if restricted else '\''
        elif char == ':':
            return '\0_\0-' if restricted else '\0 \0-'
        elif char in '\\/|*<>':
            return '\0_'
        if restricted and (char in '!&\'()[]{}$;`^,#' or char.isspace() or ord(char) > 127):
            return '' if unicodedata.category(char)[0] in 'CM' else '\0_'
        return char

    # Replace look-alike Unicode glyphs
    if restricted and (is_id is NO_DEFAULT or not is_id):
        s = unicodedata.normalize('NFKC', s)
    s = re.sub(r'[0-9]+(?::[0-9]+)+', lambda m: m.group(0).replace(':', '_'), s)  # Handle timestamps
    result = ''.join(map(replace_insane, s))
    if is_id is NO_DEFAULT:
        result = re.sub(r'(\0.)(?:(?=\1)..)+', r'\1', result)  # Remove repeated substitute chars
        STRIP_RE = r'(?:\0.|[ _-])*'
        result = re.sub(f'^\0.{STRIP_RE}|{STRIP_RE}\0.$', '', result)  # Remove substitute chars from start/end
    result = result.replace('\0', '') or '_'

    if not is_id:
        while '__' in result:
            result = result.replace('__', '_')
        result = result.strip('_')
        # Common case of "Foreign band name - English song title"
        if restricted and result.startswith('-_'):
            result = result[2:]
        if result.startswith('-'):
            result = '_' + result[len('-'):]
        result = result.lstrip('.')
        if not result:
            result = '_'
    return result


def _sanitize_path_parts(parts):
    sanitized_parts = []
    for part in parts:
        if not part or part == '.':
            continue
        elif part == '..':
            if sanitized_parts and sanitized_parts[-1] != '..':
                sanitized_parts.pop()
            else:
                sanitized_parts.append('..')
            continue
        # Replace invalid segments with `#`
        # - trailing dots and spaces (`asdf...` => `asdf..#`)
        # - invalid chars (`<>` => `##`)
        sanitized_part = re.sub(r'[/<>:"\|\\?\*]|[\s.]$', '#', part)
        sanitized_parts.append(sanitized_part)

    return sanitized_parts


def sanitize_path(s, force=False):
    """Sanitizes and normalizes path on Windows"""
    if sys.platform != 'win32':
        if not force:
            return s
        root = '/' if s.startswith('/') else ''
        path = '/'.join(_sanitize_path_parts(s.split('/')))
        return root + path if root or path else '.'

    normed = s.replace('/', '\\')

    if normed.startswith('\\\\'):
        # UNC path (`\\SERVER\SHARE`) or device path (`\\.`, `\\?`)
        parts = normed.split('\\')
        root = '\\'.join(parts[:4]) + '\\'
        parts = parts[4:]
    elif normed[1:2] == ':':
        # absolute path or drive relative path
        offset = 3 if normed[2:3] == '\\' else 2
        root = normed[:offset]
        parts = normed[offset:].split('\\')
    else:
        # relative/drive root relative path
        root = '\\' if normed[:1] == '\\' else ''
        parts = normed.split('\\')

    path = '\\'.join(_sanitize_path_parts(parts))
    return root + path if root or path else '.'


def sanitize_url(url, *, scheme='http'):
    # Prepend protocol-less URLs with `http:` scheme in order to mitigate
    # the number of unwanted failures due to missing protocol
    if url is None:
        return
    elif url.startswith('//'):
        return f'{scheme}:{url}'
    # Fix some common typos seen so far
    COMMON_TYPOS = (
        # https://github.com/ytdl-org/youtube-dl/issues/15649
        (r'^httpss://', r'https://'),
        # https://bx1.be/lives/direct-tv/
        (r'^rmtp([es]?)://', r'rtmp\1://'),
    )
    for mistake, fixup in COMMON_TYPOS:
        if re.match(mistake, url):
            return re.sub(mistake, fixup, url)
    return url


def expand_path(s):
    """Expand shell variables and ~"""
    return os.path.expandvars(compat_expanduser(s))


def to_high_limit_path(path):
    if sys.platform in ['win32', 'cygwin']:
        # Work around MAX_PATH limitation on Windows. The maximum allowed length for the individual path segments may still be quite limited.
        return '\\\\?\\' + os.path.abspath(path)

    return path


def make_dir(path, to_screen=None):
    try:
        dn = os.path.dirname(path)
        if dn:
            os.makedirs(dn, exist_ok=True)
        return True
    except OSError as err:
        if callable(to_screen) is not None:
            to_screen(f'unable to create directory {err}')
        return False


def get_executable_path():
    from ..update import _get_variant_and_executable_path

    return os.path.dirname(os.path.abspath(_get_variant_and_executable_path()[1]))


def get_user_config_dirs(package_name):
    # .config (e.g. ~/.config/package_name)
    xdg_config_home = os.getenv('XDG_CONFIG_HOME') or compat_expanduser('~/.config')
    yield os.path.join(xdg_config_home, package_name)

    # appdata (%APPDATA%/package_name)
    appdata_dir = os.getenv('appdata')
    if appdata_dir:
        yield os.path.join(appdata_dir, package_name)

    # home (~/.package_name)
    yield os.path.join(compat_expanduser('~'), f'.{package_name}')


def get_system_config_dirs(package_name):
    # /etc/package_name
    yield os.path.join('/etc', package_name)


def is_path_like(f):
    return isinstance(f, (str, bytes, os.PathLike))


@functools.cache
def get_filesystem_encoding():
    encoding = sys.getfilesystemencoding()
    return encoding if encoding is not None else 'utf-8'


def shell_quote(args, *, shell=False):
    args = list(variadic(args))

    if os.name != 'nt':
        return shlex.join(args)

    from .formatting import shell_quote as _shell_quote
    return _shell_quote(args, shell=shell)


class Popen(subprocess.Popen):
    if sys.platform == 'win32':
        _startupinfo = subprocess.STARTUPINFO()
        _startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    else:
        _startupinfo = None

    @staticmethod
    def _fix_pyinstaller_issues(env):
        if not hasattr(sys, '_MEIPASS'):
            return

        # Force spawning independent subprocesses for exes bundled with PyInstaller>=6.10
        # Ref: https://pyinstaller.org/en/v6.10.0/CHANGES.html#incompatible-changes
        #      https://github.com/yt-dlp/yt-dlp/issues/11259
        env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'

        # Restore LD_LIBRARY_PATH when using PyInstaller
        # Ref: https://pyinstaller.org/en/v6.10.0/runtime-information.html#ld-library-path-libpath-considerations
        #      https://github.com/yt-dlp/yt-dlp/issues/4573
        def _fix(key):
            orig = env.get(f'{key}_ORIG')
            if orig is None:
                env.pop(key, None)
            else:
                env[key] = orig

        _fix('LD_LIBRARY_PATH')  # Linux
        _fix('DYLD_LIBRARY_PATH')  # macOS

    def __init__(self, args, *remaining, env=None, text=False, shell=False, **kwargs):
        if env is None:
            env = os.environ.copy()
        self._fix_pyinstaller_issues(env)

        self.__text_mode = kwargs.get('encoding') or kwargs.get('errors') or text or kwargs.get('universal_newlines')
        if text is True:
            kwargs['universal_newlines'] = True  # For 3.6 compatibility
            kwargs.setdefault('encoding', 'utf-8')
            kwargs.setdefault('errors', 'replace')

        if os.name == 'nt' and kwargs.get('executable') is None:
            # Must apply shell escaping if we are trying to run a batch file
            # These conditions should be very specific to limit impact
            if not shell and isinstance(args, list) and args and args[0].lower().endswith(('.bat', '.cmd')):
                shell = True

            if shell:
                if not isinstance(args, str):
                    args = shell_quote(args, shell=True)
                shell = False
                # Set variable for `cmd.exe` newline escaping (see `utils.shell_quote`)
                env['='] = '"^\n\n"'
                args = f'{self.__comspec()} /Q /S /D /V:OFF /E:ON /C "{args}"'

        super().__init__(args, *remaining, env=env, shell=shell, **kwargs, startupinfo=self._startupinfo)

    def __comspec(self):
        comspec = os.environ.get('ComSpec') or os.path.join(
            os.environ.get('SystemRoot', ''), 'System32', 'cmd.exe')
        if os.path.isabs(comspec):
            return comspec
        raise FileNotFoundError('shell not found: neither %ComSpec% nor %SystemRoot% is set')

    def communicate_or_kill(self, *args, **kwargs):
        try:
            return self.communicate(*args, **kwargs)
        except BaseException:  # Including KeyboardInterrupt
            self.kill(timeout=None)
            raise

    def kill(self, *, timeout=0):
        super().kill()
        if timeout != 0:
            self.wait(timeout=timeout)

    @classmethod
    def run(cls, *args, timeout=None, **kwargs):
        with cls(*args, **kwargs) as proc:
            default = '' if proc.__text_mode else b''
            stdout, stderr = proc.communicate_or_kill(timeout=timeout)
            return stdout or default, stderr or default, proc.returncode


def encodeArgument(s):
    # Legacy code that uses byte strings
    # Uncomment the following line after fixing all post processors
    # assert isinstance(s, str), 'Internal error: %r should be of type %r, is %r' % (s, str, type(s))
    return s if isinstance(s, str) else s.decode('ascii')


def check_executable(exe, args=[]):
    """ Checks if the given binary is installed somewhere in PATH, and returns its name.
    args can be a list of arguments for a short output (like -version) """
    try:
        Popen.run([exe, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        return False
    return exe


def _get_exe_version_output(exe, args, ignore_return_code=False):
    try:
        # STDIN should be redirected too. On UNIX-like systems, ffmpeg triggers
        # SIGTTOU if yt-dlp is run in the background.
        # See https://github.com/ytdl-org/youtube-dl/issues/955#issuecomment-209789656
        stdout, _, ret = Popen.run([encodeArgument(exe), *args], text=True,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not ignore_return_code and ret:
            return None
    except OSError:
        return False
    return stdout


def detect_exe_version(output, version_re=None, unrecognized='present'):
    assert isinstance(output, str)
    if version_re is None:
        version_re = r'version\s+([-0-9._a-zA-Z]+)'
    m = re.search(version_re, output)
    if m:
        return m.group(1)
    else:
        return unrecognized


def parse_filesize(s):
    if s is None:
        return None

    # The lower-case forms are of course incorrect and unofficial,
    # but we support those too
    _UNIT_TABLE = {
        'B': 1,
        'b': 1,
        'bytes': 1,
        'KiB': 1024,
        'KB': 1000,
        'kB': 1024,
        'Kb': 1000,
        'kb': 1000,
        'kilobytes': 1000,
        'kibibytes': 1024,
        'MiB': 1024 ** 2,
        'MB': 1000 ** 2,
        'mB': 1024 ** 2,
        'Mb': 1000 ** 2,
        'mb': 1000 ** 2,
        'megabytes': 1000 ** 2,
        'mebibytes': 1024 ** 2,
        'GiB': 1024 ** 3,
        'GB': 1000 ** 3,
        'gB': 1024 ** 3,
        'Gb': 1000 ** 3,
        'gb': 1000 ** 3,
        'gigabytes': 1000 ** 3,
        'gibibytes': 1024 ** 3,
        'TiB': 1024 ** 4,
        'TB': 1000 ** 4,
        'tB': 1024 ** 4,
        'Tb': 1000 ** 4,
        'tb': 1000 ** 4,
        'terabytes': 1000 ** 4,
        'tebibytes': 1024 ** 4,
        'PiB': 1024 ** 5,
        'PB': 1000 ** 5,
        'pB': 1024 ** 5,
        'Pb': 1000 ** 5,
        'pb': 1000 ** 5,
        'petabytes': 1000 ** 5,
        'pebibytes': 1024 ** 5,
        'EiB': 1024 ** 6,
        'EB': 1000 ** 6,
        'eB': 1024 ** 6,
        'Eb': 1000 ** 6,
        'eb': 1000 ** 6,
        'exabytes': 1000 ** 6,
        'exbibytes': 1024 ** 6,
        'ZiB': 1024 ** 7,
        'ZB': 1000 ** 7,
        'zB': 1024 ** 7,
        'Zb': 1000 ** 7,
        'zb': 1000 ** 7,
        'zettabytes': 1000 ** 7,
        'zebibytes': 1024 ** 7,
        'YiB': 1024 ** 8,
        'YB': 1000 ** 8,
        'yB': 1024 ** 8,
        'Yb': 1000 ** 8,
        'yb': 1000 ** 8,
        'yottabytes': 1000 ** 8,
        'yobibytes': 1024 ** 8,
    }

    return lookup_unit_table(_UNIT_TABLE, s)


class _UnsafeExtensionError(Exception):
    """
    Mitigation exception for uncommon/malicious file extensions
    This should be caught in YoutubeDL.py alongside a warning

    Ref: https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-79w7-vh3h-8g4j
    """
    ALLOWED_EXTENSIONS = frozenset([
        # internal
        'description',
        'json',
        'meta',
        'orig',
        'part',
        'temp',
        'uncut',
        'unknown_video',
        'ytdl',

        # video
        *MEDIA_EXTENSIONS.video,
        'asx',
        'ismv',
        'm2t',
        'm2ts',
        'm2v',
        'm4s',
        'mng',
        'mp2v',
        'mp4v',
        'mpe',
        'mpeg',
        'mpeg1',
        'mpeg2',
        'mpeg4',
        'mxf',
        'ogm',
        'qt',
        'rm',
        'swf',
        'ts',
        'vid',
        'vob',
        'vp9',

        # audio
        *MEDIA_EXTENSIONS.audio,
        '3ga',
        'ac3',
        'adts',
        'aif',
        'au',
        'dts',
        'isma',
        'it',
        'mid',
        'mod',
        'mpga',
        'mp1',
        'mp2',
        'mp4a',
        'mpa',
        'ra',
        'shn',
        'xm',

        # image
        *MEDIA_EXTENSIONS.thumbnails,
        'avif',
        'bmp',
        'gif',
        'heic',
        'ico',
        'image',
        'jfif',
        'jng',
        'jpe',
        'jpeg',
        'jxl',
        'svg',
        'tif',
        'tiff',
        'wbmp',

        # subtitle
        *MEDIA_EXTENSIONS.subtitles,
        'dfxp',
        'fs',
        'ismt',
        'json3',
        'sami',
        'scc',
        'srv1',
        'srv2',
        'srv3',
        'ssa',
        'tt',
        'ttml',
        'xml',

        # others
        *MEDIA_EXTENSIONS.manifests,
        *MEDIA_EXTENSIONS.storyboards,
        'desktop',
        'ism',
        'm3u',
        'sbv',
        'url',
        'webloc',
    ])

    def __init__(self, extension, /):
        super().__init__(f'unsafe file extension: {extension!r}')
        self.extension = extension

    @classmethod
    def sanitize_extension(cls, extension, /, *, prepend=False):
        if extension is None:
            return None

        if '/' in extension or '\\' in extension:
            raise cls(extension)

        if not prepend:
            _, _, last = extension.rpartition('.')
            if last == 'bin':
                extension = last = 'unknown_video'
            if last.lower() not in cls.ALLOWED_EXTENSIONS:
                raise cls(extension)

        return extension


def _change_extension(prepend, filename, ext, expected_real_ext=None):
    name, real_ext = os.path.splitext(filename)

    if not expected_real_ext or real_ext[1:] == expected_real_ext:
        filename = name
        if prepend and real_ext:
            _UnsafeExtensionError.sanitize_extension(ext, prepend=True)
            return f'{filename}.{ext}{real_ext}'

    return f'{filename}.{_UnsafeExtensionError.sanitize_extension(ext)}'


prepend_extension = functools.partial(_change_extension, True)
replace_extension = functools.partial(_change_extension, False)


class LockingUnsupportedError(OSError):
    msg = 'File locking is not supported'

    def __init__(self):
        super().__init__(self.msg)


# Cross-platform file locking
if sys.platform == 'win32':
    import ctypes
    import ctypes.wintypes
    import msvcrt

    class OVERLAPPED(ctypes.Structure):
        _fields_ = [
            ('Internal', ctypes.wintypes.LPVOID),
            ('InternalHigh', ctypes.wintypes.LPVOID),
            ('Offset', ctypes.wintypes.DWORD),
            ('OffsetHigh', ctypes.wintypes.DWORD),
            ('hEvent', ctypes.wintypes.HANDLE),
        ]

    kernel32 = ctypes.WinDLL('kernel32')
    LockFileEx = kernel32.LockFileEx
    LockFileEx.argtypes = [
        ctypes.wintypes.HANDLE,     # hFile
        ctypes.wintypes.DWORD,      # dwFlags
        ctypes.wintypes.DWORD,      # dwReserved
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockLow
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockHigh
        ctypes.POINTER(OVERLAPPED),  # Overlapped
    ]
    LockFileEx.restype = ctypes.wintypes.BOOL
    UnlockFileEx = kernel32.UnlockFileEx
    UnlockFileEx.argtypes = [
        ctypes.wintypes.HANDLE,     # hFile
        ctypes.wintypes.DWORD,      # dwReserved
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockLow
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockHigh
        ctypes.POINTER(OVERLAPPED),  # Overlapped
    ]
    UnlockFileEx.restype = ctypes.wintypes.BOOL
    whole_low = 0xffffffff
    whole_high = 0x7fffffff

    def _lock_file(f, exclusive, block):
        overlapped = OVERLAPPED()
        overlapped.Offset = 0
        overlapped.OffsetHigh = 0
        overlapped.hEvent = 0
        f._lock_file_overlapped_p = ctypes.pointer(overlapped)

        if not LockFileEx(msvcrt.get_osfhandle(f.fileno()),
                          (0x2 if exclusive else 0x0) | (0x0 if block else 0x1),
                          0, whole_low, whole_high, f._lock_file_overlapped_p):
            # NB: No argument form of "ctypes.FormatError" does not work on PyPy
            raise BlockingIOError(f'Locking file failed: {ctypes.FormatError(ctypes.GetLastError())!r}')

    def _unlock_file(f):
        assert f._lock_file_overlapped_p
        handle = msvcrt.get_osfhandle(f.fileno())
        if not UnlockFileEx(handle, 0, whole_low, whole_high, f._lock_file_overlapped_p):
            raise OSError(f'Unlocking file failed: {ctypes.FormatError(ctypes.GetLastError())!r}')

else:
    try:
        import fcntl

        def _lock_file(f, exclusive, block):
            flags = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            if not block:
                flags |= fcntl.LOCK_NB
            try:
                fcntl.flock(f, flags)
            except BlockingIOError:
                raise
            except OSError:  # AOSP does not have flock()
                fcntl.lockf(f, flags)

        def _unlock_file(f):
            with contextlib.suppress(OSError):
                return fcntl.flock(f, fcntl.LOCK_UN)
            with contextlib.suppress(OSError):
                return fcntl.lockf(f, fcntl.LOCK_UN)  # AOSP does not have flock()
            return fcntl.flock(f, fcntl.LOCK_UN | fcntl.LOCK_NB)  # virtiofs needs LOCK_NB on unlocking

    except ImportError:

        def _lock_file(f, exclusive, block):
            raise LockingUnsupportedError

        def _unlock_file(f):
            raise LockingUnsupportedError


class locked_file:
    locked = False

    def __init__(self, filename, mode, block=True, encoding=None):
        if mode not in {'r', 'rb', 'a', 'ab', 'w', 'wb'}:
            raise NotImplementedError(mode)
        self.mode, self.block = mode, block

        writable = any(f in mode for f in 'wax+')
        readable = any(f in mode for f in 'r+')
        flags = functools.reduce(operator.ior, (
            getattr(os, 'O_CLOEXEC', 0),  # UNIX only
            getattr(os, 'O_BINARY', 0),  # Windows only
            getattr(os, 'O_NOINHERIT', 0),  # Windows only
            os.O_CREAT if writable else 0,  # O_TRUNC only after locking
            os.O_APPEND if 'a' in mode else 0,
            os.O_EXCL if 'x' in mode else 0,
            os.O_RDONLY if not writable else os.O_RDWR if readable else os.O_WRONLY,
        ))

        self.f = os.fdopen(os.open(filename, flags, 0o666), mode, encoding=encoding)

    def __enter__(self):
        exclusive = 'r' not in self.mode
        try:
            _lock_file(self.f, exclusive, self.block)
            self.locked = True
        except OSError:
            self.f.close()
            raise
        if 'w' in self.mode:
            try:
                self.f.truncate()
            except OSError as e:
                if e.errno not in (errno.EINVAL, errno.ESPIPE):  # invalid argument, illegal seek
                    raise
        return self.f

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if self.locked:
                self.unlock()
        finally:
            self.f.close()

    def unlock(self):
        if not self.locked:
            return
        _unlock_file(self.f)
        self.locked = False
        
    def open(self):
        return self.__enter__()
    
    def close(self):
        self.unlock()
        self.f.close()
