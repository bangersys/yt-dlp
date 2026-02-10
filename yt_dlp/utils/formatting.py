import functools
import locale
import os
import re
import sys

from ..constants import ACCENT_CHARS
from ..globals import WINDOWS_VT_MODE


@functools.cache
def preferredencoding():
    """Get preferred encoding.

    Returns the best encoding scheme for the system, based on
    locale.getpreferredencoding() and some further tweaks.
    """
    try:
        pref = locale.getpreferredencoding()
        'TEST'.encode(pref)
    except Exception:
        pref = 'UTF-8'

    return pref


@functools.cache
def supports_terminal_sequences(stream):
    if os.name == 'nt':
        if not WINDOWS_VT_MODE.value:
            return False
    elif not os.getenv('TERM'):
        return False
    try:
        return stream.isatty()
    except BaseException:
        return False


def write_string(s, out=None, encoding=None):
    assert isinstance(s, str)
    out = out or sys.stderr
    # `sys.stderr` might be `None` (Ref: https://github.com/pyinstaller/pyinstaller/pull/7217)
    if not out:
        return

    if sys.platform == 'win32' and supports_terminal_sequences(out):
        s = re.sub(r'([\r\n]+)', r' \1', s)

    enc, buffer = None, out
    # `mode` might be `None` (Ref: https://github.com/yt-dlp/yt-dlp/issues/8816)
    if 'b' in (getattr(out, 'mode', None) or ''):
        enc = encoding or preferredencoding()
    elif hasattr(out, 'buffer'):
        buffer = out.buffer
        enc = encoding or getattr(out, 'encoding', None) or preferredencoding()

    buffer.write(s.encode(enc, 'ignore') if enc else s)
    out.flush()


__all__ = [
    'ACCENT_CHARS',
    'preferredencoding',
    'supports_terminal_sequences',
    'write_string',
]
