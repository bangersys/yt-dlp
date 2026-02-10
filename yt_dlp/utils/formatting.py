import collections.abc
import functools
import inspect
import locale
import math
import os
import re
import shlex
import sys

from ..constants import CMD_QUOTE_TRANS, IDENTITY, NO_DEFAULT, WINDOWS_QUOTE_TRANS
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


def bug_reports_message(before=';'):
    from ..update import REPOSITORY

    msg = (f'please report this issue on  https://github.com/{REPOSITORY}/issues?q= , '
           'filling out the appropriate issue template. Confirm you are on the latest version using  yt-dlp -U')

    return f'{before} {msg}'


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


def partial_application(func):
    sig = inspect.signature(func)
    required_args = [
        param.name for param in sig.parameters.values()
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        if param.default is inspect.Parameter.empty
    ]

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if set(required_args[len(args):]).difference(kwargs):
            return functools.partial(func, *args, **kwargs)
        return func(*args, **kwargs)

    return wrapped


def is_iterable_like(x, allowed_types=collections.abc.Iterable, blocked_types=NO_DEFAULT):
    if blocked_types is NO_DEFAULT:
        blocked_types = (str, bytes, collections.abc.Mapping)
    return isinstance(x, allowed_types) and not isinstance(x, blocked_types)


def variadic(x, allowed_types=NO_DEFAULT):
    if allowed_types is not NO_DEFAULT:
        if not isinstance(allowed_types, (tuple, type)):
            from ._utils import deprecation_warning
            deprecation_warning('allowed_types should be a tuple or a type')
            allowed_types = tuple(allowed_types)
        return x if is_iterable_like(x, blocked_types=allowed_types) else (x, )
    return x if is_iterable_like(x) else (x, )


@partial_application
def int_or_none(v, scale=1, default=None, get_attr=None, invscale=1, base=None):
    if get_attr and v is not None:
        v = getattr(v, get_attr, None)
    if invscale == 1 and scale < 1:
        invscale = int(1 / scale)
        scale = 1
    try:
        return (int(v) if base is None else int(v, base=base)) * invscale // scale
    except (ValueError, TypeError, OverflowError):
        return default


def str_or_none(v, default=None):
    return default if v is None else str(v)


def str_to_int(int_str):
    """A more relaxed version of int_or_none."""
    if isinstance(int_str, int):
        return int_str
    elif isinstance(int_str, str):
        int_str = re.sub(r'[,\.\+]', '', int_str)
        return int_or_none(int_str)


@partial_application
def float_or_none(v, scale=1, invscale=1, default=None):
    if v is None:
        return default
    if invscale == 1 and scale < 1:
        invscale = int(1 / scale)
        scale = 1
    try:
        return float(v) * invscale / scale
    except (ValueError, TypeError):
        return default


def bool_or_none(v, default=None):
    return v if isinstance(v, bool) else default


def strip_or_none(v, default=None):
    return v.strip() if isinstance(v, str) else default


def url_or_none(url):
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    return url if re.match(r'(?:(?:https?|rt(?:m(?:pt?[es]?|fp)|sp[su]?)|mms|ftps?|wss?):)?//', url) else None


def format_decimal_suffix(num, fmt='%d%s', *, factor=1000):
    """Formats numbers with decimal suffixes like K, M, etc."""
    num, factor = float_or_none(num), float(factor)
    if num is None or num < 0:
        return None
    possible_suffixes = 'kMGTPEZY'
    exponent = 0 if num == 0 else min(int(math.log(num, factor)), len(possible_suffixes))
    suffix = ['', *possible_suffixes][exponent]
    if factor == 1024:
        suffix = {'k': 'Ki', '': ''}.get(suffix, f'{suffix}i')
    converted = num / (factor ** exponent)
    return fmt % (converted, suffix)


def format_bytes(bytes):
    return format_decimal_suffix(bytes, '%.2f%sB', factor=1024) or 'N/A'


@partial_application
def format_field(obj, field=None, template='%s', ignore=NO_DEFAULT, default='', func=IDENTITY):
    from .traversal import traverse_obj

    val = traverse_obj(obj, *variadic(field))
    if not val if ignore is NO_DEFAULT else val in variadic(ignore):
        return default
    return template % func(val)


def remove_start(s, start):
    return s[len(start):] if s is not None and s.startswith(start) else s


def remove_end(s, end):
    return s[:-len(end)] if s is not None and end and s.endswith(end) else s


def remove_quotes(s):
    if s is None or len(s) < 2:
        return s
    for quote in ('"', "'"):
        if s[0] == quote and s[-1] == quote:
            return s[1:-1]
    return s


_terminal_sequences_re = re.compile('\033\\[[^m]+m')


def remove_terminal_sequences(string):
    """Remove ANSI escape sequences from a string."""
    return _terminal_sequences_re.sub('', string)


def join_nonempty(*values, delim='-', from_dict=None):
    if from_dict is not None:
        from .traversal import traverse_obj

        values = (traverse_obj(from_dict, variadic(v)) for v in values)
    return delim.join(map(str, filter(None, values)))


@partial_application
def truncate_string(s, left, right=0):
    assert left > 3 and right >= 0
    if s is None or len(s) <= left + right:
        return s
    return f'{s[:left - 3]}...{s[-right:] if right else ""}'


_windows_quote_trans = str.maketrans(WINDOWS_QUOTE_TRANS)
_cmd_quote_trans = str.maketrans(CMD_QUOTE_TRANS)


def shell_quote(args, *, shell=False):
    args = list(variadic(args))

    if os.name != 'nt':
        return shlex.join(args)

    trans = _cmd_quote_trans if shell else _windows_quote_trans
    return ' '.join(
        s if re.fullmatch(r'[\w#$*\-+./:?@\\]+', s, re.ASCII)
        else re.sub(r'(\\+)("|$)', r'\1\1\2', s).translate(trans).join('""')
        for s in args)


def args_to_str(args):
    return shell_quote(args)


def error_to_str(err):
    return f'{type(err).__name__}: {err}'


def number_of_digits(number):
    return len('%d' % number)
__all__ = [
    'ACCENT_CHARS',
    'preferredencoding',
    'supports_terminal_sequences',
    'write_string',
]
