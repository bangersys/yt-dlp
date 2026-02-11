import contextlib
import functools
import os
import platform
import re
import ssl
import subprocess
import sys

from ..globals import IN_CLI
from .formatting import format_field, join_nonempty, variadic
from .types import bug_reports_message, YoutubeDLError


@functools.cache
def system_identifier():
    python_implementation = platform.python_implementation()
    if python_implementation == 'PyPy' and hasattr(sys, 'pypy_version_info'):
        python_implementation += ' version %d.%d.%d' % sys.pypy_version_info[:3]
    libc_ver = []
    with contextlib.suppress(OSError):  # We may not have access to the executable
        libc_ver = platform.libc_ver()

    return 'Python {} ({} {} {}) - {} ({}{})'.format(
        platform.python_version(),
        python_implementation,
        platform.machine(),
        platform.architecture()[0],
        platform.platform(),
        ssl.OPENSSL_VERSION,
        format_field(join_nonempty(*libc_ver, delim=' '), None, ', %s'),
    )


def version_tuple(v, *, lenient=False):
    from .formatting import int_or_none
    parse = int_or_none(default=-1) if lenient else int
    return tuple(parse(e) for e in re.split(r'[-.]', v))


def is_outdated_version(version, limit, assume_new=True):
    if not version:
        return not assume_new
    try:
        return version_tuple(version) < version_tuple(limit)
    except ValueError:
        return not assume_new


def ytdl_is_updateable():
    """ Returns if yt-dlp can be updated with -U """
    from ..update import is_non_updateable
    return not is_non_updateable()


@functools.cache
def get_windows_version():
    """ Get Windows version. returns () if it's not running on Windows """
    if os.name == 'nt':
        return version_tuple(platform.win32_ver()[1])
    else:
        return ()


def _get_exe_version_output(exe, args, ignore_return_code=False):
    from .filesystem import Popen
    from ._utils import encodeArgument
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


def get_exe_version(exe, args=['--version'],
                    version_re=None, unrecognized=('present', 'broken')):
    """ Returns the version of the specified executable,
    or False if the executable is not present """
    unrecognized = variadic(unrecognized)
    assert len(unrecognized) in (1, 2)
    out = _get_exe_version_output(exe, args)
    if out is None:
        return unrecognized[-1]
    return out and detect_exe_version(out, version_re, unrecognized[0])


__all__ = [
    'detect_exe_version',
    'get_exe_version',
    'get_windows_version',
    'is_outdated_version',
    'system_identifier',
    'version_tuple',
    'ytdl_is_updateable',
]
