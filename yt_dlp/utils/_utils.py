import base64
from .types import *
import binascii
import calendar
import codecs
import collections
import collections.abc
import contextlib
import datetime as dt
import email.header
import email.utils
import enum
import functools
import hashlib
import hmac
import inspect
import io
import itertools
import json
import locale
import math
import mimetypes
import netrc
import operator
import os
import platform
import random
import re
import shlex
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import time
import types
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree

from .formatting import *

from ..constants import (
    ACCENT_CHARS,
    BOMS,
    COUNTRY_IP_MAP,
    COUNTRY_MAP,
    DATE_FORMATS,
    DATE_FORMATS_DAY_FIRST,
    DATE_FORMATS_MONTH_FIRST,
    DEFAULT_OUTTMPL,
    ENGLISH_MONTH_NAMES,
    FILE_SIZE_UNITS,
    JSON_LD_RE,
    KNOWN_EXTENSIONS,
    LINK_TEMPLATES,
    MEDIA_EXTENSIONS,
    MONTH_NAMES,
    NUMBER_RE,
    OUTTMPL_TYPES,
    PACKED_CODES_RE,
    POSTPROCESS_WHEN,
    STR_FORMAT_RE_TMPL,
    STR_FORMAT_TYPES,
    TIMEZONE_NAMES,
    TV_PARENTAL_GUIDELINES,
    US_RATINGS,
)

from ..compat import (
    compat_datetime_from_timestamp,
    compat_etree_fromstring,
    compat_expanduser,
    compat_HTMLParseError,
)
from ..dependencies import xattr
from ..globals import IN_CLI

from .types import *
from .datetime import (
    DateRange,
    date_formats,
    date_from_str,
    datetime_add_months,
    datetime_from_str,
    datetime_round,
    extract_timezone,
    formatSeconds,
    hyphenate_date,
    month_by_abbreviation,
    month_by_name,
    parse_duration,
    parse_iso8601,
    strftime_or_none,
    timeconvert,
    timetuple_from_msec,
    unified_strdate,
    unified_timestamp,
)
from .networking import (
    base_url,
    extract_basic_auth,
    get_domain,
    multipart_encode,
    smuggle_url,
    unsmuggle_url,
    update_url,
    update_url_query,
    url_basename,
    urlencode_postdata,
    urljoin,
)
from .parsing import (
    lookup_unit_table,
    parse_age_limit,
    parse_bitrate,
    parse_bytes,
    parse_count,
    parse_filesize,
    parse_qs,
    parse_resolution,
)
from .locking import LockingUnsupportedError, locked_file
from .formatting import preferredencoding, supports_terminal_sequences, variadic, write_string
from .json import NO_DEFAULT

from .version import (
    detect_exe_version,
    get_exe_version,
    get_windows_version,
    is_outdated_version,
    system_identifier,
    version_tuple,
    ytdl_is_updateable,
)

__name__ = __name__.rsplit('.', 1)[0]  # noqa: A001 # Pretend to be the parent module



# moved to constants.py



def write_json_file(obj, fn):
    """ Encode obj as JSON and write it to fn, atomically if possible """

    tf = tempfile.NamedTemporaryFile(
        prefix=f'{os.path.basename(fn)}.', dir=os.path.dirname(fn),
        suffix='.tmp', delete=False, mode='w', encoding='utf-8')

    try:
        with tf:
            json.dump(obj, tf, ensure_ascii=False)
        if sys.platform == 'win32':
            # Need to remove existing file on Windows, else os.rename raises
            # WindowsError or FileExistsError.
            with contextlib.suppress(OSError):
                os.unlink(fn)
        with contextlib.suppress(OSError):
            mask = os.umask(0)
            os.umask(mask)
            os.chmod(tf.name, 0o666 & ~mask)
        os.rename(tf.name, fn)
    except Exception:
        with contextlib.suppress(OSError):
            os.remove(tf.name)
        raise


# TODO: Use global logger
def deprecation_warning(msg, *, printer=None, stacklevel=0, **kwargs):
    if IN_CLI.value:
        if msg in deprecation_warning._cache:
            return
        deprecation_warning._cache.add(msg)
        if printer:
            return printer(f'{msg}{bug_reports_message()}', **kwargs)
        return write_string(f'ERROR: {msg}{bug_reports_message()}\n', **kwargs)
    else:
        import warnings
        warnings.warn(DeprecationWarning(msg), stacklevel=stacklevel + 3)


deprecation_warning._cache = set()



from .xml import *








# XXX: This should be far less strict


















class LenientJSONDecoder(json.JSONDecoder):
    # TODO: Write tests
    def __init__(self, *args, transform_source=None, ignore_extra=False, close_objects=0, **kwargs):
        self.transform_source, self.ignore_extra = transform_source, ignore_extra
        self._close_attempts = 2 * close_objects
        super().__init__(*args, **kwargs)

    @staticmethod
    def _close_object(err):
        doc = err.doc[:err.pos]
        # We need to add comma first to get the correct error message
        if err.msg.startswith('Expecting \',\''):
            return doc + ','
        elif not doc.endswith(','):
            return

        if err.msg.startswith('Expecting property name'):
            return doc[:-1] + '}'
        elif err.msg.startswith('Expecting value'):
            return doc[:-1] + ']'

    def decode(self, s):
        if self.transform_source:
            s = self.transform_source(s)
        for attempt in range(self._close_attempts + 1):
            try:
                if self.ignore_extra:
                    return self.raw_decode(s.lstrip())[0]
                return super().decode(s)
            except json.JSONDecodeError as e:
                if e.pos is None:
                    raise
                elif attempt < self._close_attempts:
                    s = self._close_object(e)
                    if s is not None:
                        continue
                raise type(e)(f'{e.msg} in {s[e.pos - 10:e.pos + 10]!r}', s, e.pos)
        assert False, 'Too many attempts to decode JSON'


from .filesystem import (
    Popen,
    _get_exe_version_output,
    check_executable,
    encodeArgument,
    expand_path,
    get_executable_path,
    get_filesystem_encoding,
    get_system_config_dirs,
    get_user_config_dirs,
    is_path_like,
    locked_file,
    make_dir,
    parse_filesize,
    prepend_extension,
    replace_extension,
    sanitize_filename,
    sanitize_open,
    sanitize_path,
    sanitize_url,
    shell_quote,
    to_high_limit_path,
)

# Move these to re-exports
# sanitize_open is imported above

# sanitize_open is imported above










def orderedSet(iterable, *, lazy=False):
    """Remove all duplicates from the input iterable"""
    def _iter():
        seen = []  # Do not use set since the items can be unhashable
        for x in iterable:
            if x not in seen:
                seen.append(x)
                yield x

    return _iter() if lazy else list(_iter())











class netrc_from_content(netrc.netrc):
    def __init__(self, content):
        self.hosts, self.macros = {}, {}
        with io.StringIO(content) as stream:
            self._parse('-', stream, False)



def encodeArgument(s):
    # Legacy code that uses byte strings
    # Uncomment the following line after fixing all post processors
    # assert isinstance(s, str), 'Internal error: %r should be of type %r, is %r' % (s, str, type(s))
    return s if isinstance(s, str) else s.decode('ascii')





def is_path_like(f):
    return isinstance(f, (str, bytes, os.PathLike))





@partial_application
def determine_ext(url, default_ext='unknown_video'):
    if url is None or '.' not in url:
        return default_ext
    guess = url.partition('?')[0].rpartition('.')[2]
    if re.match(r'^[A-Za-z0-9]+$', guess):
        return guess
    # Try extract ext from URLs like http://example.com/foo/bar.mp4/?download
    elif guess.rstrip('/') in KNOWN_EXTENSIONS:
        return guess.rstrip('/')
    else:
        return default_ext



from .subtitles import *





@functools.cache









# Cross-platform file locking






@functools.cache
def get_filesystem_encoding():
    encoding = sys.getfilesystemencoding()
    return encoding if encoding is not None else 'utf-8'













def setproctitle(title):
    assert isinstance(title, str)

    # Workaround for https://github.com/yt-dlp/yt-dlp/issues/4541
    try:
        import ctypes
    except ImportError:
        return

    try:
        libc = ctypes.cdll.LoadLibrary('libc.so.6')
    except OSError:
        return
    except TypeError:
        # LoadLibrary in Windows Python 2.7.13 only expects
        # a bytestring, but since unicode_literals turns
        # every string into a unicode string, it fails.
        return
    title_bytes = title.encode()
    buf = ctypes.create_string_buffer(len(title_bytes))
    buf.value = title_bytes
    try:
        # PR_SET_NAME = 15      Ref: /usr/include/linux/prctl.h
        libc.prctl(15, buf, 0, 0, 0)
    except AttributeError:
        return  # Strange libc, just skip this











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


def check_executable(exe, args=[]):
    """ Checks if the given binary is installed somewhere in PATH, and returns its name.
    args can be a list of arguments for a short output (like -version) """
    try:
        Popen.run([exe, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        return False
    return exe




def frange(start=0, stop=None, step=1):
    """Float range"""
    if stop is None:
        start, stop = 0, start
    sign = [-1, 1][step > 0] if step else 0
    while sign * start < sign * stop:
        yield start
        start += step


class PlaylistEntries:
    MissingEntry = object()
    is_exhausted = False

    def __init__(self, ydl, info_dict):
        self.ydl = ydl

        # _entries must be assigned now since infodict can change during iteration
        entries = info_dict.get('entries')
        from .types import LazyList
        if entries is None:
            raise EntryNotInPlaylist('There are no entries')
        elif isinstance(entries, list):
            self.is_exhausted = True

        requested_entries = info_dict.get('requested_entries')
        self.is_incomplete = requested_entries is not None
        if self.is_incomplete:
            assert self.is_exhausted
            self._entries = [self.MissingEntry] * max(requested_entries or [0])
            for i, entry in zip(requested_entries, entries):  # noqa: B905
                self._entries[i - 1] = entry
        elif isinstance(entries, (list, PagedList, LazyList)):
            self._entries = entries
        else:
            self._entries = LazyList(entries)

    PLAYLIST_ITEMS_RE = re.compile(r'''(?x)
        (?P<start>[+-]?\d+)?
        (?P<range>[:-]
            (?P<end>[+-]?\d+|inf(?:inite)?)?
            (?::(?P<step>[+-]?\d+))?
        )?''')

    @classmethod
    def parse_playlist_items(cls, string):
        for segment in string.split(','):
            if not segment:
                raise ValueError('There is two or more consecutive commas')
            mobj = cls.PLAYLIST_ITEMS_RE.fullmatch(segment)
            if not mobj:
                raise ValueError(f'{segment!r} is not a valid specification')
            start, end, step, has_range = mobj.group('start', 'end', 'step', 'range')
            if int_or_none(step) == 0:
                raise ValueError(f'Step in {segment!r} cannot be zero')
            yield slice(int_or_none(start), float_or_none(end), int_or_none(step)) if has_range else int(start)

    def get_requested_items(self):
        playlist_items = self.ydl.params.get('playlist_items')
        playlist_start = self.ydl.params.get('playliststart', 1)
        playlist_end = self.ydl.params.get('playlistend')
        # For backwards compatibility, interpret -1 as whole list
        if playlist_end in (-1, None):
            playlist_end = ''
        if not playlist_items:
            playlist_items = f'{playlist_start}:{playlist_end}'
        elif playlist_start != 1 or playlist_end:
            self.ydl.report_warning('Ignoring playliststart and playlistend because playlistitems was given', only_once=True)

        for index in self.parse_playlist_items(playlist_items):
            for i, entry in self[index]:
                yield i, entry
                if not entry:
                    continue
                try:
                    # The item may have just been added to archive. Don't break due to it
                    if not self.ydl.params.get('lazy_playlist'):
                        # TODO: Add auto-generated fields
                        self.ydl._match_entry(entry, incomplete=True, silent=True)
                except (ExistingVideoReached, RejectedVideoReached):
                    return

    def get_full_count(self):
        if self.is_exhausted and not self.is_incomplete:
            return len(self)
        elif isinstance(self._entries, InAdvancePagedList):
            if self._entries._pagesize == 1:
                return self._entries._pagecount

    @functools.cached_property
    def _getter(self):
        if isinstance(self._entries, list):
            def get_entry(i):
                try:
                    entry = self._entries[i]
                except IndexError:
                    entry = self.MissingEntry
                    if not self.is_incomplete:
                        raise self.IndexError
                if entry is self.MissingEntry:
                    raise EntryNotInPlaylist(f'Entry {i + 1} cannot be found')
                return entry
        else:
            def get_entry(i):
                try:
                    from .types import LazyList
                    return type(self.ydl)._handle_extraction_exceptions(lambda _, i: self._entries[i])(self.ydl, i)
                except (LazyList.IndexError, PagedList.IndexError):
                    raise self.IndexError
        return get_entry

    def __getitem__(self, idx):
        if isinstance(idx, int):
            idx = slice(idx, idx)

        # NB: PlaylistEntries[1:10] => (0, 1, ... 9)
        step = 1 if idx.step is None else idx.step
        if idx.start is None:
            start = 0 if step > 0 else len(self) - 1
        else:
            start = idx.start - 1 if idx.start >= 0 else len(self) + idx.start

        # NB: Do not call len(self) when idx == [:]
        if idx.stop is None:
            stop = 0 if step < 0 else float('inf')
        else:
            stop = idx.stop - 1 if idx.stop >= 0 else len(self) + idx.stop
        stop += [-1, 1][step > 0]

        for i in frange(start, stop, step):
            if i < 0:
                continue
            try:
                entry = self._getter(i)
            except self.IndexError:
                self.is_exhausted = True
                if step > 0:
                    break
                continue
            yield i + 1, entry

    def __len__(self):
        return len(tuple(self[:]))

    class IndexError(IndexError):  # noqa: A001
        pass








def read_batch_urls(batch_fd):
    def fixup(url):
        if not isinstance(url, str):
            url = url.decode('utf-8', 'replace')
        BOM_UTF8 = ('\xef\xbb\xbf', '\ufeff')
        for bom in BOM_UTF8:
            if url.startswith(bom):
                url = url[len(bom):]
        url = url.lstrip()
        if not url or url.startswith(('#', ';', ']')):
            return False
        # "#" cannot be stripped out since it is part of the URI
        # However, it can be safely stripped out if following a whitespace
        return re.split(r'\s#', url, maxsplit=1)[0].rstrip()

    with contextlib.closing(batch_fd) as fd:
        return [url for url in map(fixup, fd) if url]





def try_call(*funcs, expected_type=None, args=[], kwargs={}):
    for f in funcs:
        try:
            val = f(*args, **kwargs)
        except (AttributeError, KeyError, TypeError, IndexError, ValueError, ZeroDivisionError):
            pass
        else:
            if expected_type is None or isinstance(val, expected_type):
                return val


def try_get(src, getter, expected_type=None):
    return try_call(*variadic(getter), args=(src,), expected_type=expected_type)


def filter_dict(dct, cndn=lambda _, v: v is not None):
    return {k: v for k, v in dct.items() if cndn(k, v)}


def merge_dicts(*dicts):
    merged = {}
    for a_dict in dicts:
        for k, v in a_dict.items():
            if ((v is not None and k not in merged)
                    or (isinstance(v, str) and merged[k] == '')):
                merged[k] = v
    return merged


def encode_compat_str(string, encoding=preferredencoding(), errors='strict'):
    return string if isinstance(string, str) else str(string, encoding, errors)





def strip_jsonp(code):
    return re.sub(
        r'''(?sx)^
            (?:window\.)?(?P<func_name>[a-zA-Z0-9_.$]*)
            (?:\s*&&\s*(?P=func_name))?
            \s*\(\s*(?P<callback_data>.*)\);?
            \s*?(?://[^\n]*)*$''',
        r'\g<callback_data>', code)


def js_to_json(code, vars={}, *, strict=False):
    # vars is a dict of var, val pairs to substitute
    STRING_QUOTES = '\'"`'
    STRING_RE = '|'.join(rf'{q}(?:\\.|[^\\{q}])*{q}' for q in STRING_QUOTES)
    COMMENT_RE = r'/\*(?:(?!\*/).)*?\*/|//[^\n]*\n'
    SKIP_RE = fr'\s*(?:{COMMENT_RE})?\s*'
    INTEGER_TABLE = (
        (fr'(?s)^(0[xX][0-9a-fA-F]+){SKIP_RE}:?$', 16),
        (fr'(?s)^(0+[0-7]+){SKIP_RE}:?$', 8),
    )

    def process_escape(match):
        JSON_PASSTHROUGH_ESCAPES = R'"\bfnrtu'
        escape = match.group(1) or match.group(2)

        return (Rf'\{escape}' if escape in JSON_PASSTHROUGH_ESCAPES
                else R'\u00' if escape == 'x'
                else '' if escape == '\n'
                else escape)

    def template_substitute(match):
        evaluated = js_to_json(match.group(1), vars, strict=strict)
        if evaluated[0] == '"':
            with contextlib.suppress(json.JSONDecodeError):
                return json.loads(evaluated)
        return evaluated

    def fix_kv(m):
        v = m.group(0)
        if v in ('true', 'false', 'null'):
            return v
        elif v in ('undefined', 'void 0'):
            return 'null'
        elif v.startswith(('/*', '//', '!')) or v == ',':
            return ''

        if v[0] in STRING_QUOTES:
            v = re.sub(r'(?s)\${([^}]+)}', template_substitute, v[1:-1]) if v[0] == '`' else v[1:-1]
            escaped = re.sub(r'(?s)(")|\\(.)', process_escape, v)
            return f'"{escaped}"'

        for regex, base in INTEGER_TABLE:
            im = re.match(regex, v)
            if im:
                i = int(im.group(1), base)
                return f'"{i}":' if v.endswith(':') else str(i)

        if v in vars:
            try:
                if not strict:
                    json.loads(vars[v])
            except json.JSONDecodeError:
                return json.dumps(vars[v])
            else:
                return vars[v]

        if not strict:
            return f'"{v}"'

        raise ValueError(f'Unknown value: {v}')

    def create_map(mobj):
        return json.dumps(dict(json.loads(js_to_json(mobj.group(1) or '[]', vars=vars))))

    code = re.sub(r'(?:new\s+)?Array\((.*?)\)', r'[\g<1>]', code)
    code = re.sub(r'new Map\((\[.*?\])?\)', create_map, code)
    if not strict:
        code = re.sub(rf'new Date\(({STRING_RE})\)', r'\g<1>', code)
        code = re.sub(r'new \w+\((.*?)\)', lambda m: json.dumps(m.group(0)), code)
        code = re.sub(r'parseInt\([^\d]+(\d+)[^\d]+\)', r'\1', code)
        code = re.sub(r'\(function\([^)]*\)\s*\{[^}]*\}\s*\)\s*\(\s*(["\'][^)]*["\'])\s*\)', r'\1', code)

    return re.sub(rf'''(?sx)
        {STRING_RE}|
        {COMMENT_RE}|,(?={SKIP_RE}[\]}}])|
        void\s0|(?:(?<![0-9])[eE]|[a-df-zA-DF-Z_$])[.a-zA-Z_$0-9]*|
        \b(?:0[xX][0-9a-fA-F]+|(?<!\.)0+[0-7]+)(?:{SKIP_RE}:)?|
        [0-9]+(?={SKIP_RE}:)|
        !+
        ''', fix_kv, code)


def qualities(quality_ids):
    """ Get a numeric quality value out of a list of possible values """
    def q(qid):
        try:
            return quality_ids.index(qid)
        except ValueError:
            return -1
    return q



# moved to constants.py










@partial_application
def mimetype2ext(mt, default=NO_DEFAULT):
    if not isinstance(mt, str):
        if default is not NO_DEFAULT:
            return default
        return None

    MAP = {
        # video
        '3gpp': '3gp',
        'mp2t': 'ts',
        'mp4': 'mp4',
        'mpeg': 'mpeg',
        'mpegurl': 'm3u8',
        'quicktime': 'mov',
        'webm': 'webm',
        'vp9': 'vp9',
        'video/ogg': 'ogv',
        'x-flv': 'flv',
        'x-m4v': 'm4v',
        'x-matroska': 'mkv',
        'x-mng': 'mng',
        'x-mp4-fragmented': 'mp4',
        'x-ms-asf': 'asf',
        'x-ms-wmv': 'wmv',
        'x-msvideo': 'avi',
        'vnd.dlna.mpeg-tts': 'mpeg',

        # application (streaming playlists)
        'dash+xml': 'mpd',
        'f4m+xml': 'f4m',
        'hds+xml': 'f4m',
        'vnd.apple.mpegurl': 'm3u8',
        'vnd.ms-sstr+xml': 'ism',
        'x-mpegurl': 'm3u8',

        # audio
        'audio/mp4': 'm4a',
        # Per RFC 3003, audio/mpeg can be .mp1, .mp2 or .mp3.
        # Using .mp3 as it's the most popular one
        'audio/mpeg': 'mp3',
        'audio/webm': 'webm',
        'audio/x-matroska': 'mka',
        'audio/x-mpegurl': 'm3u',
        'aacp': 'aac',
        'flac': 'flac',
        'midi': 'mid',
        'ogg': 'ogg',
        'wav': 'wav',
        'wave': 'wav',
        'x-aac': 'aac',
        'x-flac': 'flac',
        'x-m4a': 'm4a',
        'x-realaudio': 'ra',
        'x-wav': 'wav',

        # image
        'avif': 'avif',
        'bmp': 'bmp',
        'gif': 'gif',
        'jpeg': 'jpg',
        'png': 'png',
        'svg+xml': 'svg',
        'tiff': 'tif',
        'vnd.wap.wbmp': 'wbmp',
        'webp': 'webp',
        'x-icon': 'ico',
        'x-jng': 'jng',
        'x-ms-bmp': 'bmp',

        # caption
        'filmstrip+json': 'fs',
        'smptett+xml': 'tt',
        'ttaf+xml': 'dfxp',
        'ttml+xml': 'ttml',
        'x-ms-sami': 'sami',
        'x-subrip': 'srt',
        'x-srt': 'srt',

        # misc
        'gzip': 'gz',
        'json': 'json',
        'xml': 'xml',
        'zip': 'zip',
    }

    mimetype = mt.partition(';')[0].strip().lower()
    _, _, subtype = mimetype.rpartition('/')

    from .traversal import traverse_obj
    ext = traverse_obj(MAP, mimetype, subtype, subtype.rsplit('+')[-1])
    if ext:
        return ext
    elif default is not NO_DEFAULT:
        return default
    return subtype.replace('+', '.')


def ext2mimetype(ext_or_url):
    if not ext_or_url:
        return None
    if '.' not in ext_or_url:
        ext_or_url = f'file.{ext_or_url}'
    return mimetypes.guess_type(ext_or_url)[0]


def parse_codecs(codecs_str):
    # http://tools.ietf.org/html/rfc6381
    if not codecs_str:
        return {}
    split_codecs = list(filter(None, map(
        str.strip, codecs_str.strip().strip(',').split(','))))
    vcodec, acodec, scodec, hdr = None, None, None, None
    for full_codec in split_codecs:
        full_codec = re.sub(r'^([^.]+)', lambda m: m.group(1).lower(), full_codec)
        parts = re.sub(r'0+(?=\d)', '', full_codec).split('.')
        if parts[0] in ('avc1', 'avc2', 'avc3', 'avc4', 'vp9', 'vp8', 'hev1', 'hev2',
                        'h263', 'h264', 'mp4v', 'hvc1', 'av1', 'theora', 'dvh1', 'dvhe'):
            if vcodec:
                continue
            vcodec = full_codec
            if parts[0] in ('dvh1', 'dvhe'):
                hdr = 'DV'
            elif parts[0] == 'av1':
                from .traversal import traverse_obj
                if traverse_obj(parts, 3) == '10':
                    hdr = 'HDR10'
            elif parts[:2] == ['vp9', '2']:
                hdr = 'HDR10'
        elif parts[0] in ('flac', 'mp4a', 'opus', 'vorbis', 'mp3', 'aac', 'ac-4',
                          'ac-3', 'ec-3', 'eac3', 'dtsc', 'dtse', 'dtsh', 'dtsl'):
            acodec = acodec or full_codec
        elif parts[0] in ('stpp', 'wvtt'):
            scodec = scodec or full_codec
        else:
            write_string(f'WARNING: Unknown codec {full_codec}\n')
    if vcodec or acodec or scodec:
        return {
            'vcodec': vcodec or 'none',
            'acodec': acodec or 'none',
            'dynamic_range': hdr,
            **({'scodec': scodec} if scodec is not None else {}),
        }
    elif len(split_codecs) == 2:
        return {
            'vcodec': split_codecs[0],
            'acodec': split_codecs[1],
        }
    return {}


def get_compatible_ext(*, vcodecs, acodecs, vexts, aexts, preferences=None):
    assert len(vcodecs) == len(vexts) and len(acodecs) == len(aexts)

    allow_mkv = not preferences or 'mkv' in preferences

    if allow_mkv and max(len(acodecs), len(vcodecs)) > 1:
        return 'mkv'  # TODO: any other format allows this?

    # TODO: All codecs supported by parse_codecs isn't handled here
    COMPATIBLE_CODECS = {
        'mp4': {
            'av1', 'hevc', 'avc1', 'mp4a', 'ac-4',  # fourcc (m3u8, mpd)
            'h264', 'aacl', 'ec-3',  # Set in ISM
        },
        'webm': {
            'av1', 'vp9', 'vp8', 'opus', 'vrbs',
            'vp9x', 'vp8x',  # in the webm spec
        },
    }

    sanitize_codec = functools.partial(
        try_get, getter=lambda x: x[0].split('.')[0].replace('0', '').lower())
    vcodec, acodec = sanitize_codec(vcodecs), sanitize_codec(acodecs)

    for ext in preferences or COMPATIBLE_CODECS.keys():
        codec_set = COMPATIBLE_CODECS.get(ext, set())
        if ext == 'mkv' or codec_set.issuperset((vcodec, acodec)):
            return ext

    COMPATIBLE_EXTS = (
        {'mp3', 'mp4', 'm4a', 'm4p', 'm4b', 'm4r', 'm4v', 'ismv', 'isma', 'mov'},
        {'webm', 'weba'},
    )
    for ext in preferences or vexts:
        current_exts = {ext, *vexts, *aexts}
        if ext == 'mkv' or current_exts == {ext} or any(
                ext_sets.issuperset(current_exts) for ext_sets in COMPATIBLE_EXTS):
            return ext
    return 'mkv' if allow_mkv else preferences[-1]


def urlhandle_detect_ext(url_handle, default=NO_DEFAULT):
    getheader = url_handle.headers.get

    if cd := getheader('Content-Disposition'):
        if m := re.match(r'attachment;\s*filename="(?P<filename>[^"]+)"', cd):
            if ext := determine_ext(m.group('filename'), default_ext=None):
                return ext

    return (
        determine_ext(getheader('x-amz-meta-name'), default_ext=None)
        or getheader('x-amz-meta-file-type')
        or mimetype2ext(getheader('Content-Type'), default=default))


def encode_data_uri(data, mime_type):
    return 'data:{};base64,{}'.format(mime_type, base64.b64encode(data).decode('ascii'))


def age_restricted(content_limit, age_limit):
    """ Returns True iff the content should be blocked """

    if age_limit is None:  # No limit set
        return False
    if content_limit is None:
        return False  # Content available for everyone
    return age_limit < content_limit



# moved to constants.py


def is_html(first_bytes):
    """ Detect whether a file contains HTML by examining its first bytes. """

    encoding = 'utf-8'
    for bom, enc in BOMS:
        while first_bytes.startswith(bom):
            encoding, first_bytes = enc, first_bytes[len(bom):]

    return re.match(r'\s*<', first_bytes.decode(encoding, 'replace'))


def determine_protocol(info_dict):
    protocol = info_dict.get('protocol')
    if protocol is not None:
        return protocol

    url = sanitize_url(info_dict['url'])
    if url.startswith('rtmp'):
        return 'rtmp'
    elif url.startswith('mms'):
        return 'mms'
    elif url.startswith('rtsp'):
        return 'rtsp'

    ext = determine_ext(url)
    if ext == 'm3u8':
        return 'm3u8' if info_dict.get('is_live') else 'm3u8_native'
    elif ext == 'f4m':
        return 'f4m'

    return urllib.parse.urlparse(url).scheme


def render_table(header_row, data, delim=False, extra_gap=0, hide_empty=False):
    """ Render a list of rows, each as a list of values.
    Text after a \t will be right aligned """
    def width(string):
        return len(remove_terminal_sequences(string).replace('\t', ''))

    def get_max_lens(table):
        return [max(width(str(v)) for v in col) for col in zip(*table, strict=True)]

    def filter_using_list(row, filter_array):
        return [col for take, col in itertools.zip_longest(filter_array, row, fillvalue=True) if take]

    max_lens = get_max_lens(data) if hide_empty else []
    header_row = filter_using_list(header_row, max_lens)
    data = [filter_using_list(row, max_lens) for row in data]

    table = [header_row, *data]
    max_lens = get_max_lens(table)
    extra_gap += 1
    if delim:
        table = [header_row, [delim * (ml + extra_gap) for ml in max_lens], *data]
        table[1][-1] = table[1][-1][:-extra_gap * len(delim)]  # Remove extra_gap from end of delimiter
    for row in table:
        for pos, text in enumerate(map(str, row)):
            if '\t' in text:
                row[pos] = text.replace('\t', ' ' * (max_lens[pos] - width(text))) + ' ' * extra_gap
            else:
                row[pos] = text + ' ' * (max_lens[pos] - width(text) + extra_gap)
    return '\n'.join(''.join(row).rstrip() for row in table)


def _match_one(filter_part, dct, incomplete):
    # TODO: Generalize code with YoutubeDL._build_format_filter
    STRING_OPERATORS = {
        '*=': operator.contains,
        '^=': lambda attr, value: attr.startswith(value),
        '$=': lambda attr, value: attr.endswith(value),
        '~=': lambda attr, value: re.search(value, attr),
    }
    COMPARISON_OPERATORS = {
        **STRING_OPERATORS,
        '<=': operator.le,  # "<=" must be defined above "<"
        '<': operator.lt,
        '>=': operator.ge,
        '>': operator.gt,
        '=': operator.eq,
    }

    if isinstance(incomplete, bool):
        is_incomplete = lambda _: incomplete
    else:
        is_incomplete = lambda k: k in incomplete

    operator_rex = re.compile(r'''(?x)
        (?P<key>[a-z_]+)
        \s*(?P<negation>!\s*)?(?P<op>{})(?P<none_inclusive>\s*\?)?\s*
        (?:
            (?P<quote>["\'])(?P<quotedstrval>.+?)(?P=quote)|
            (?P<strval>.+?)
        )
        '''.format('|'.join(map(re.escape, COMPARISON_OPERATORS.keys()))))
    m = operator_rex.fullmatch(filter_part.strip())
    if m:
        m = m.groupdict()
        unnegated_op = COMPARISON_OPERATORS[m['op']]
        if m['negation']:
            op = lambda attr, value: not unnegated_op(attr, value)
        else:
            op = unnegated_op
        comparison_value = m['quotedstrval'] or m['strval']
        if m['quote']:
            comparison_value = comparison_value.replace(r'\{}'.format(m['quote']), m['quote'])
        actual_value = dct.get(m['key'])
        numeric_comparison = None
        if isinstance(actual_value, (int, float)):
            # If the original field is a string and matching comparisonvalue is
            # a number we should respect the origin of the original field
            # and process comparison value as a string (see
            # https://github.com/ytdl-org/youtube-dl/issues/11082)
            try:
                numeric_comparison = int(comparison_value)
            except ValueError:
                numeric_comparison = parse_filesize(comparison_value)
                if numeric_comparison is None:
                    numeric_comparison = parse_filesize(f'{comparison_value}B')
                if numeric_comparison is None:
                    numeric_comparison = parse_duration(comparison_value)
        if numeric_comparison is not None and m['op'] in STRING_OPERATORS:
            raise ValueError('Operator {} only supports string values!'.format(m['op']))
        if actual_value is None:
            return is_incomplete(m['key']) or m['none_inclusive']
        return op(actual_value, comparison_value if numeric_comparison is None else numeric_comparison)

    UNARY_OPERATORS = {
        '': lambda v: (v is True) if isinstance(v, bool) else (v is not None),
        '!': lambda v: (v is False) if isinstance(v, bool) else (v is None),
    }
    operator_rex = re.compile(r'''(?x)
        (?P<op>{})\s*(?P<key>[a-z_]+)
        '''.format('|'.join(map(re.escape, UNARY_OPERATORS.keys()))))
    m = operator_rex.fullmatch(filter_part.strip())
    if m:
        op = UNARY_OPERATORS[m.group('op')]
        actual_value = dct.get(m.group('key'))
        if is_incomplete(m.group('key')) and actual_value is None:
            return True
        return op(actual_value)

    raise ValueError(f'Invalid filter part {filter_part!r}')


def match_str(filter_str, dct, incomplete=False):
    """ Filter a dictionary with a simple string syntax.
    @returns           Whether the filter passes
    @param incomplete  Set of keys that is expected to be missing from dct.
                       Can be True/False to indicate all/none of the keys may be missing.
                       All conditions on incomplete keys pass if the key is missing
    """
    return all(
        _match_one(filter_part.replace(r'\&', '&'), dct, incomplete)
        for filter_part in re.split(r'(?<!\\)&', filter_str))


def match_filter_func(filters, breaking_filters=None):
    if not filters and not breaking_filters:
        return None
    repr_ = f'{match_filter_func.__module__}.{match_filter_func.__qualname__}({filters}, {breaking_filters})'

    breaking_filters = match_filter_func(breaking_filters) or (lambda _, __: None)
    filters = set(variadic(filters or []))

    interactive = '-' in filters
    if interactive:
        filters.remove('-')

    @function_with_repr.set_repr(repr_)
    def _match_func(info_dict, incomplete=False):
        ret = breaking_filters(info_dict, incomplete)
        if ret is not None:
            raise RejectedVideoReached(ret)

        if not filters or any(match_str(f, info_dict, incomplete) for f in filters):
            return NO_DEFAULT if interactive and not incomplete else None
        else:
            video_title = info_dict.get('title') or info_dict.get('id') or 'entry'
            filter_str = ') | ('.join(map(str.strip, filters))
            return f'{video_title} does not pass filter ({filter_str}), skipping ..'
    return _match_func









# ISO3166Utils and GeoUtils moved to yt_dlp.utils.geo
from .geo import GeoUtils, ISO3166Utils


# Both long_to_bytes and bytes_to_long are adapted from PyCrypto, which is
# released into Public Domain
# https://github.com/dlitz/pycrypto/blob/master/lib/Crypto/Util/number.py#L387

from .crypto import *


def parse_m3u8_attributes(attrib):
    info = {}
    for (key, val) in re.findall(r'(?P<key>[A-Z0-9-]+)=(?P<val>"[^"]+"|[^",]+)(?:,|$)', attrib):
        if val.startswith('"'):
            val = val[1:-1]
        info[key] = val
    return info



def write_xattr(path, key, value):
    # Windows: Write xattrs to NTFS Alternate Data Streams:
    # http://en.wikipedia.org/wiki/NTFS#Alternate_data_streams_.28ADS.29
    if os.name == 'nt':
        assert ':' not in key
        assert os.path.exists(path)

        try:
            with open(f'{path}:{key}', 'wb') as f:
                f.write(value)
        except OSError as e:
            raise XAttrMetadataError(e.errno, e.strerror)
        return

    # UNIX Method 1. Use os.setxattr/xattrs/pyxattrs modules

    setxattr = None
    if callable(getattr(os, 'setxattr', None)):
        setxattr = os.setxattr
    elif getattr(xattr, '_yt_dlp__identifier', None) == 'pyxattr':
        # Unicode arguments are not supported in pyxattr until version 0.5.0
        # See https://github.com/ytdl-org/youtube-dl/issues/5498
        if version_tuple(xattr.__version__) >= (0, 5, 0):
            setxattr = xattr.set
    elif xattr:
        setxattr = xattr.setxattr

    if setxattr:
        try:
            setxattr(path, key, value)
        except OSError as e:
            raise XAttrMetadataError(e.errno, e.strerror)
        return

    # UNIX Method 2. Use setfattr/xattr executables
    exe = ('setfattr' if check_executable('setfattr', ['--version'])
           else 'xattr' if check_executable('xattr', ['-h']) else None)
    if not exe:
        raise XAttrUnavailableError(
            'Couldn\'t find a tool to set the xattrs. Install either the "xattr" or "pyxattr" Python modules or the '
            + ('"xattr" binary' if sys.platform != 'linux' else 'GNU "attr" package (which contains the "setfattr" tool)'))

    value = value.decode()
    try:
        _, stderr, returncode = Popen.run(
            [exe, '-w', key, value, path] if exe == 'xattr' else [exe, '-n', key, '-v', value, path],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    except OSError as e:
        raise XAttrMetadataError(e.errno, e.strerror)
    if returncode:
        raise XAttrMetadataError(returncode, stderr)


def random_birthday(year_field, month_field, day_field):
    start_date = dt.date(1950, 1, 1)
    end_date = dt.date(1995, 12, 31)
    offset = random.randint(0, (end_date - start_date).days)
    random_date = start_date + dt.timedelta(offset)
    return {
        year_field: str(random_date.year),
        month_field: str(random_date.month),
        day_field: str(random_date.day),
    }


def find_available_port(interface=''):
    try:
        with socket.socket() as sock:
            sock.bind((interface, 0))
            return sock.getsockname()[1]
    except OSError:
        return None



# moved to constants.py


def iri_to_uri(iri):
    """
    Converts an IRI (Internationalized Resource Identifier, allowing Unicode characters) to a URI (Uniform Resource Identifier, ASCII-only).

    The function doesn't add an additional layer of escaping; e.g., it doesn't escape `%3C` as `%253C`. Instead, it percent-escapes characters with an underlying UTF-8 encoding *besides* those already escaped, leaving the URI intact.
    """

    iri_parts = urllib.parse.urlparse(iri)

    if '[' in iri_parts.netloc:
        raise ValueError('IPv6 URIs are not, yet, supported.')
        # Querying `.netloc`, when there's only one bracket, also raises a ValueError.

    # The `safe` argument values, that the following code uses, contain the characters that should not be percent-encoded. Everything else but letters, digits and '_.-' will be percent-encoded with an underlying UTF-8 encoding. Everything already percent-encoded will be left as is.

    net_location = ''
    if iri_parts.username:
        net_location += urllib.parse.quote(iri_parts.username, safe=r"!$%&'()*+,~")
        if iri_parts.password is not None:
            net_location += ':' + urllib.parse.quote(iri_parts.password, safe=r"!$%&'()*+,~")
        net_location += '@'

    net_location += iri_parts.hostname.encode('idna').decode()  # Punycode for Unicode hostnames.
    # The 'idna' encoding produces ASCII text.
    if iri_parts.port is not None and iri_parts.port != 80:
        net_location += ':' + str(iri_parts.port)

    return urllib.parse.urlunparse(
        (iri_parts.scheme,
            net_location,

            urllib.parse.quote_plus(iri_parts.path, safe=r"!$%&'()*+,/:;=@|~"),

            # Unsure about the `safe` argument, since this is a legacy way of handling parameters.
            urllib.parse.quote_plus(iri_parts.params, safe=r"!$%&'()*+,/:;=@|~"),

            # Not totally sure about the `safe` argument, since the source does not explicitly mention the query URI component.
            urllib.parse.quote_plus(iri_parts.query, safe=r"!$%&'()*+,/:;=?@{|}~"),

            urllib.parse.quote_plus(iri_parts.fragment, safe=r"!#$%&'()*+,/:;=?@{|}~")))

    # Source for `safe` arguments: https://url.spec.whatwg.org/#percent-encoded-bytes.


def to_high_limit_path(path):
    if sys.platform in ['win32', 'cygwin']:
        # Work around MAX_PATH limitation on Windows. The maximum allowed length for the individual path segments may still be quite limited.
        return '\\\\?\\' + os.path.abspath(path)

    return path


def clean_podcast_url(url):
    url = re.sub(r'''(?x)
        (?:
            (?:
                chtbl\.com/track|
                media\.blubrry\.com| # https://create.blubrry.com/resources/podcast-media-download-statistics/getting-started/
                play\.podtrac\.com|
                chrt\.fm/track|
                mgln\.ai/e
            )(?:/[^/.]+)?|
            (?:dts|www)\.podtrac\.com/(?:pts/)?redirect\.[0-9a-z]{3,4}| # http://analytics.podtrac.com/how-to-measure
            flex\.acast\.com|
            pd(?:
                cn\.co| # https://podcorn.com/analytics-prefix/
                st\.fm # https://podsights.com/docs/
            )/e|
            [0-9]\.gum\.fm|
            pscrb\.fm/rss/p
        )/''', '', url)
    return re.sub(r'^\w+://(\w+://)', r'\1', url)


_HEX_TABLE = '0123456789abcdef'


def random_uuidv4():
    return re.sub(r'[xy]', lambda x: _HEX_TABLE[random.randint(0, 15)], 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx')


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


def time_seconds(**kwargs):
    """
    Returns TZ-aware time in seconds since the epoch (1970-01-01T00:00:00Z)
    """
    return time.time() + dt.timedelta(**kwargs).total_seconds()


# implemented following JWT https://www.rfc-editor.org/rfc/rfc7519.html
# implemented following JWS https://www.rfc-editor.org/rfc/rfc7515.html


# can be extended in future to verify the signature and parse header and return the algorithm used if it's not HS256



def windows_enable_vt_mode():
    """Ref: https://bugs.python.org/issue30075 """
    if get_windows_version() < (10, 0, 10586):
        return

    import ctypes
    import ctypes.wintypes
    import msvcrt

    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

    dll = ctypes.WinDLL('kernel32', use_last_error=False)
    handle = os.open('CONOUT$', os.O_RDWR)
    try:
        h_out = ctypes.wintypes.HANDLE(msvcrt.get_osfhandle(handle))
        dw_original_mode = ctypes.wintypes.DWORD()
        success = dll.GetConsoleMode(h_out, ctypes.byref(dw_original_mode))
        if not success:
            raise Exception('GetConsoleMode failed')

        success = dll.SetConsoleMode(h_out, ctypes.wintypes.DWORD(
            dw_original_mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING))
        if not success:
            raise Exception('SetConsoleMode failed')
    finally:
        os.close(handle)

    WINDOWS_VT_MODE.value = True
    supports_terminal_sequences.cache_clear()



def scale_thumbnails_to_max_format_width(formats, thumbnails, url_width_re):
    """
    Find the largest format dimensions in terms of video width and, for each thumbnail:
    * Modify the URL: Match the width with the provided regex and replace with the former width
    * Update dimensions

    This function is useful with video services that scale the provided thumbnails on demand
    """
    _keys = ('width', 'height')
    max_dimensions = max(
        (tuple(fmt.get(k) or 0 for k in _keys) for fmt in formats),
        default=(0, 0))
    if not max_dimensions[0]:
        return thumbnails
    return [
        merge_dicts(
            {'url': re.sub(url_width_re, str(max_dimensions[0]), thumbnail['url'])},
            dict(zip(_keys, max_dimensions, strict=True)), thumbnail)
        for thumbnail in thumbnails
    ]


def parse_http_range(range):
    """ Parse value of "Range" or "Content-Range" HTTP header into tuple. """
    if not range:
        return None, None, None
    crg = re.search(r'bytes[ =](\d+)-(\d+)?(?:/(\d+))?', range)
    if not crg:
        return None, None, None
    return int(crg.group(1)), int_or_none(crg.group(2)), int_or_none(crg.group(3))


def read_stdin(what):
    if what:
        eof = 'Ctrl+Z' if os.name == 'nt' else 'Ctrl+D'
        write_string(f'Reading {what} from STDIN - EOF ({eof}) to end:\n')
    return sys.stdin


def determine_file_encoding(data):
    """
    Detect the text encoding used
    @returns (encoding, bytes to skip)
    """

    # BOM marks are given priority over declarations
    for bom, enc in BOMS:
        if data.startswith(bom):
            return enc, len(bom)

    # Strip off all null bytes to match even when UTF-16 or UTF-32 is used.
    # We ignore the endianness to get a good enough match
    data = data.replace(b'\0', b'')
    mobj = re.match(rb'(?m)^#\s*coding\s*:\s*(\S+)\s*$', data)
    return mobj.group(1).decode() if mobj else None, 0


class Config:
    own_args = None
    parsed_args = None
    filename = None
    __initialized = False

    def __init__(self, parser, label=None):
        self.parser, self.label = parser, label
        self._loaded_paths, self.configs = set(), []

    def init(self, args=None, filename=None):
        assert not self.__initialized
        self.own_args, self.filename = args, filename
        return self.load_configs()

    def load_configs(self):
        directory = ''
        if self.filename:
            location = os.path.realpath(self.filename)
            directory = os.path.dirname(location)
            if location in self._loaded_paths:
                return False
            self._loaded_paths.add(location)

        self.__initialized = True
        opts, _ = self.parser.parse_known_args(self.own_args)
        self.parsed_args = self.own_args
        for location in opts.config_locations or []:
            if location == '-':
                if location in self._loaded_paths:
                    continue
                self._loaded_paths.add(location)
                self.append_config(shlex.split(read_stdin('options'), comments=True), label='stdin')
                continue
            location = os.path.join(directory, expand_path(location))
            if os.path.isdir(location):
                location = os.path.join(location, 'yt-dlp.conf')
            if not os.path.exists(location):
                self.parser.error(f'config location {location} does not exist')
            self.append_config(self.read_file(location), location)
        return True

    def __str__(self):
        label = join_nonempty(
            self.label, 'config', f'"{self.filename}"' if self.filename else '',
            delim=' ')
        return join_nonempty(
            self.own_args is not None and f'{label[0].upper()}{label[1:]}: {self.hide_login_info(self.own_args)}',
            *(f'\n{c}'.replace('\n', '\n| ')[1:] for c in self.configs),
            delim='\n')

    @staticmethod
    def read_file(filename, default=[]):
        try:
            optionf = open(filename, 'rb')
        except OSError:
            return default  # silently skip if file is not present
        try:
            enc, skip = determine_file_encoding(optionf.read(512))
            optionf.seek(skip, io.SEEK_SET)
        except OSError:
            enc = None  # silently skip read errors
        try:
            # FIXME: https://github.com/ytdl-org/youtube-dl/commit/dfe5fa49aed02cf36ba9f743b11b0903554b5e56
            contents = optionf.read().decode(enc or preferredencoding())
            res = shlex.split(contents, comments=True)
        except Exception as err:
            raise ValueError(f'Unable to parse "{filename}": {err}')
        finally:
            optionf.close()
        return res

    @staticmethod
    def hide_login_info(opts):
        PRIVATE_OPTS = {'-p', '--password', '-u', '--username', '--video-password', '--ap-password', '--ap-username'}
        eqre = re.compile('^(?P<key>' + ('|'.join(re.escape(po) for po in PRIVATE_OPTS)) + ')=.+$')

        def _scrub_eq(o):
            m = eqre.match(o)
            if m:
                return m.group('key') + '=PRIVATE'
            else:
                return o

        opts = list(map(_scrub_eq, opts))
        for idx, opt in enumerate(opts):
            if opt in PRIVATE_OPTS and idx + 1 < len(opts):
                opts[idx + 1] = 'PRIVATE'
        return opts

    def append_config(self, *args, label=None):
        config = type(self)(self.parser, label)
        config._loaded_paths = self._loaded_paths
        if config.init(*args):
            self.configs.append(config)

    @property
    def all_args(self):
        for config in reversed(self.configs):
            yield from config.all_args
        yield from self.parsed_args or []

    def parse_known_args(self, **kwargs):
        return self.parser.parse_known_args(self.all_args, **kwargs)

    def parse_args(self):
        return self.parser.parse_args(self.all_args)


def merge_headers(*dicts):
    """Merge dicts of http headers case insensitively, prioritizing the latter ones"""
    return {k.title(): v for k, v in itertools.chain.from_iterable(map(dict.items, dicts))}




# removed Namespace and MEDIA_EXTENSIONS (moved to constants.py)


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




@partial_application
def make_archive_id(ie, video_id):
    ie_key = ie if isinstance(ie, str) else ie.ie_key()
    return f'{ie_key.lower()} {video_id}'


def orderedSet_from_options(options, alias_dict, *, use_regex=False, start=None):
    assert 'all' in alias_dict, '"all" alias is required'
    requested = list(start or [])
    for val in options:
        discard = val.startswith('-')
        if discard:
            val = val[1:]

        if val in alias_dict:
            val = alias_dict[val] if not discard else [
                i[1:] if i.startswith('-') else f'-{i}' for i in alias_dict[val]]
            # NB: Do not allow regex in aliases for performance
            requested = orderedSet_from_options(val, alias_dict, start=requested)
            continue

        current = (filter(re.compile(val, re.I).fullmatch, alias_dict['all']) if use_regex
                   else [val] if val in alias_dict['all'] else None)
        if current is None:
            raise ValueError(val)

        if discard:
            for item in current:
                while item in requested:
                    requested.remove(item)
        else:
            requested.extend(current)

    return orderedSet(requested)


# TODO: Rewrite
class FormatSorter:
    regex = r' *((?P<reverse>\+)?(?P<field>[a-zA-Z0-9_]+)((?P<separator>[~:])(?P<limit>.*?))?)? *$'

    default = ('hidden', 'aud_or_vid', 'hasvid', 'ie_pref', 'lang', 'quality',
               'res', 'fps', 'hdr:12', 'vcodec', 'channels', 'acodec',
               'size', 'br', 'asr', 'proto', 'ext', 'hasaud', 'source', 'id')  # These must not be aliases
    _prefer_vp9_sort = ('hidden', 'aud_or_vid', 'hasvid', 'ie_pref', 'lang', 'quality',
                        'res', 'fps', 'hdr:12', 'vcodec:vp9.2', 'channels', 'acodec',
                        'size', 'br', 'asr', 'proto', 'ext', 'hasaud', 'source', 'id')
    ytdl_default = ('hasaud', 'lang', 'quality', 'tbr', 'filesize', 'vbr',
                    'height', 'width', 'proto', 'vext', 'abr', 'aext',
                    'fps', 'fs_approx', 'source', 'id')

    settings = {
        'vcodec': {'type': 'ordered', 'regex': True,
                   'order': ['av0?1', r'vp0?9\.0?2', 'vp0?9', '[hx]265|he?vc?', '[hx]264|avc', 'vp0?8', 'mp4v|h263', 'theora', '', None, 'none']},
        'acodec': {'type': 'ordered', 'regex': True,
                   'order': ['[af]lac', 'wav|aiff', 'opus', 'vorbis|ogg', 'aac', 'mp?4a?', 'mp3', 'ac-?4', 'e-?a?c-?3', 'ac-?3', 'dts', '', None, 'none']},
        'hdr': {'type': 'ordered', 'regex': True, 'field': 'dynamic_range',
                'order': ['dv', '(hdr)?12', r'(hdr)?10\+', '(hdr)?10', 'hlg', '', 'sdr', None]},
        'proto': {'type': 'ordered', 'regex': True, 'field': 'protocol',
                  'order': ['(ht|f)tps', '(ht|f)tp$', 'm3u8.*', '.*dash', 'websocket_frag', 'rtmpe?', '', 'mms|rtsp', 'ws|websocket', 'f4']},
        'vext': {'type': 'ordered', 'field': 'video_ext',
                 'order': ('mp4', 'mov', 'webm', 'flv', '', 'none'),
                 'order_free': ('webm', 'mp4', 'mov', 'flv', '', 'none')},
        'aext': {'type': 'ordered', 'regex': True, 'field': 'audio_ext',
                 'order': ('m4a', 'aac', 'mp3', 'ogg', 'opus', 'web[am]', '', 'none'),
                 'order_free': ('ogg', 'opus', 'web[am]', 'mp3', 'm4a', 'aac', '', 'none')},
        'hidden': {'visible': False, 'forced': True, 'type': 'extractor', 'max': -1000},
        'aud_or_vid': {'visible': False, 'forced': True, 'type': 'multiple',
                       'field': ('vcodec', 'acodec'),
                       'function': lambda it: int(any(v != 'none' for v in it))},
        'ie_pref': {'priority': True, 'type': 'extractor'},
        'hasvid': {'priority': True, 'field': 'vcodec', 'type': 'boolean', 'not_in_list': ('none',)},
        'hasaud': {'field': 'acodec', 'type': 'boolean', 'not_in_list': ('none',)},
        'lang': {'convert': 'float', 'field': 'language_preference', 'default': -1},
        'quality': {'convert': 'float', 'default': -1},
        'filesize': {'convert': 'bytes'},
        'fs_approx': {'convert': 'bytes', 'field': 'filesize_approx'},
        'id': {'convert': 'string', 'field': 'format_id'},
        'height': {'convert': 'float_none'},
        'width': {'convert': 'float_none'},
        'fps': {'convert': 'float_none'},
        'channels': {'convert': 'float_none', 'field': 'audio_channels'},
        'tbr': {'convert': 'float_none'},
        'vbr': {'convert': 'float_none'},
        'abr': {'convert': 'float_none'},
        'asr': {'convert': 'float_none'},
        'source': {'convert': 'float', 'field': 'source_preference', 'default': -1},

        'codec': {'type': 'combined', 'field': ('vcodec', 'acodec')},
        'br': {'type': 'multiple', 'field': ('tbr', 'vbr', 'abr'), 'convert': 'float_none',
               'function': lambda it: next(filter(None, it), None)},
        'size': {'type': 'multiple', 'field': ('filesize', 'fs_approx'), 'convert': 'bytes',
                 'function': lambda it: next(filter(None, it), None)},
        'ext': {'type': 'combined', 'field': ('vext', 'aext')},
        'res': {'type': 'multiple', 'field': ('height', 'width'),
                'function': lambda it: min(filter(None, it), default=0)},

        # Actual field names
        'format_id': {'type': 'alias', 'field': 'id'},
        'preference': {'type': 'alias', 'field': 'ie_pref'},
        'language_preference': {'type': 'alias', 'field': 'lang'},
        'source_preference': {'type': 'alias', 'field': 'source'},
        'protocol': {'type': 'alias', 'field': 'proto'},
        'filesize_approx': {'type': 'alias', 'field': 'fs_approx'},
        'audio_channels': {'type': 'alias', 'field': 'channels'},

        # Deprecated
        'dimension': {'type': 'alias', 'field': 'res', 'deprecated': True},
        'resolution': {'type': 'alias', 'field': 'res', 'deprecated': True},
        'extension': {'type': 'alias', 'field': 'ext', 'deprecated': True},
        'bitrate': {'type': 'alias', 'field': 'br', 'deprecated': True},
        'total_bitrate': {'type': 'alias', 'field': 'tbr', 'deprecated': True},
        'video_bitrate': {'type': 'alias', 'field': 'vbr', 'deprecated': True},
        'audio_bitrate': {'type': 'alias', 'field': 'abr', 'deprecated': True},
        'framerate': {'type': 'alias', 'field': 'fps', 'deprecated': True},
        'filesize_estimate': {'type': 'alias', 'field': 'size', 'deprecated': True},
        'samplerate': {'type': 'alias', 'field': 'asr', 'deprecated': True},
        'video_ext': {'type': 'alias', 'field': 'vext', 'deprecated': True},
        'audio_ext': {'type': 'alias', 'field': 'aext', 'deprecated': True},
        'video_codec': {'type': 'alias', 'field': 'vcodec', 'deprecated': True},
        'audio_codec': {'type': 'alias', 'field': 'acodec', 'deprecated': True},
        'video': {'type': 'alias', 'field': 'hasvid', 'deprecated': True},
        'has_video': {'type': 'alias', 'field': 'hasvid', 'deprecated': True},
        'audio': {'type': 'alias', 'field': 'hasaud', 'deprecated': True},
        'has_audio': {'type': 'alias', 'field': 'hasaud', 'deprecated': True},
        'extractor': {'type': 'alias', 'field': 'ie_pref', 'deprecated': True},
        'extractor_preference': {'type': 'alias', 'field': 'ie_pref', 'deprecated': True},
    }

    def __init__(self, ydl, field_preference):
        self.ydl = ydl
        self._order = []
        self.evaluate_params(self.ydl.params, field_preference)
        if ydl.params.get('verbose'):
            self.print_verbose_info(self.ydl.write_debug)

    def _get_field_setting(self, field, key):
        if field not in self.settings:
            if key in ('forced', 'priority'):
                return False
            self.ydl.deprecated_feature(f'Using arbitrary fields ({field}) for format sorting is '
                                        'deprecated and may be removed in a future version')
            self.settings[field] = {}
        prop_obj = self.settings[field]
        if key not in prop_obj:
            type_ = prop_obj.get('type')
            if key == 'field':
                default = 'preference' if type_ == 'extractor' else (field,) if type_ in ('combined', 'multiple') else field
            elif key == 'convert':
                default = 'order' if type_ == 'ordered' else 'float_string' if field else 'ignore'
            else:
                default = {'type': 'field', 'visible': True, 'order': [], 'not_in_list': (None,)}.get(key)
            prop_obj[key] = default
        return prop_obj[key]

    def _resolve_field_value(self, field, value, convert_none=False):
        if value is None:
            if not convert_none:
                return None
        else:
            value = value.lower()
        conversion = self._get_field_setting(field, 'convert')
        if conversion == 'ignore':
            return None
        if conversion == 'string':
            return value
        elif conversion == 'float_none':
            return float_or_none(value)
        elif conversion == 'bytes':
            return parse_bytes(value)
        elif conversion == 'order':
            order_list = (self._use_free_order and self._get_field_setting(field, 'order_free')) or self._get_field_setting(field, 'order')
            use_regex = self._get_field_setting(field, 'regex')
            list_length = len(order_list)
            empty_pos = order_list.index('') if '' in order_list else list_length + 1
            if use_regex and value is not None:
                for i, regex in enumerate(order_list):
                    if regex and re.match(regex, value):
                        return list_length - i
                return list_length - empty_pos  # not in list
            else:  # not regex or  value = None
                return list_length - (order_list.index(value) if value in order_list else empty_pos)
        else:
            if value.isnumeric():
                return float(value)
            else:
                self.settings[field]['convert'] = 'string'
                return value

    def evaluate_params(self, params, sort_extractor):
        self._use_free_order = params.get('prefer_free_formats', False)
        self._sort_user = params.get('format_sort', [])
        self._sort_extractor = sort_extractor

        def add_item(field, reverse, closest, limit_text):
            field = field.lower()
            if field in self._order:
                return
            self._order.append(field)
            limit = self._resolve_field_value(field, limit_text)
            data = {
                'reverse': reverse,
                'closest': False if limit is None else closest,
                'limit_text': limit_text,
                'limit': limit}
            if field in self.settings:
                self.settings[field].update(data)
            else:
                self.settings[field] = data

        sort_list = (
            tuple(field for field in self.default if self._get_field_setting(field, 'forced'))
            + (tuple() if params.get('format_sort_force', False)
                else tuple(field for field in self.default if self._get_field_setting(field, 'priority')))
            + tuple(self._sort_user) + tuple(sort_extractor) + self.default)

        for item in sort_list:
            match = re.match(self.regex, item)
            if match is None:
                raise ExtractorError(f'Invalid format sort string "{item}" given by extractor')
            field = match.group('field')
            if field is None:
                continue
            if self._get_field_setting(field, 'type') == 'alias':
                alias, field = field, self._get_field_setting(field, 'field')
                if self._get_field_setting(alias, 'deprecated'):
                    self.ydl.deprecated_feature(f'Format sorting alias {alias} is deprecated and may '
                                                f'be removed in a future version. Please use {field} instead')
            reverse = match.group('reverse') is not None
            closest = match.group('separator') == '~'
            limit_text = match.group('limit')

            has_limit = limit_text is not None
            has_multiple_fields = self._get_field_setting(field, 'type') == 'combined'
            has_multiple_limits = has_limit and has_multiple_fields and not self._get_field_setting(field, 'same_limit')

            fields = self._get_field_setting(field, 'field') if has_multiple_fields else (field,)
            limits = limit_text.split(':') if has_multiple_limits else (limit_text,) if has_limit else tuple()
            limit_count = len(limits)
            for (i, f) in enumerate(fields):
                add_item(f, reverse, closest,
                         limits[i] if i < limit_count
                         else limits[0] if has_limit and not has_multiple_limits
                         else None)

    def print_verbose_info(self, write_debug):
        if self._sort_user:
            write_debug('Sort order given by user: {}'.format(', '.join(self._sort_user)))
        if self._sort_extractor:
            write_debug('Sort order given by extractor: {}'.format(', '.join(self._sort_extractor)))
        write_debug('Formats sorted by: {}'.format(', '.join(['{}{}{}'.format(
            '+' if self._get_field_setting(field, 'reverse') else '', field,
            '{}{}({})'.format('~' if self._get_field_setting(field, 'closest') else ':',
                              self._get_field_setting(field, 'limit_text'),
                              self._get_field_setting(field, 'limit'))
            if self._get_field_setting(field, 'limit_text') is not None else '')
            for field in self._order if self._get_field_setting(field, 'visible')])))

    def _calculate_field_preference_from_value(self, format_, field, type_, value):
        reverse = self._get_field_setting(field, 'reverse')
        closest = self._get_field_setting(field, 'closest')
        limit = self._get_field_setting(field, 'limit')

        if type_ == 'extractor':
            maximum = self._get_field_setting(field, 'max')
            if value is None or (maximum is not None and value >= maximum):
                value = -1
        elif type_ == 'boolean':
            in_list = self._get_field_setting(field, 'in_list')
            not_in_list = self._get_field_setting(field, 'not_in_list')
            value = 0 if ((in_list is None or value in in_list) and (not_in_list is None or value not in not_in_list)) else -1
        elif type_ == 'ordered':
            value = self._resolve_field_value(field, value, True)

        # try to convert to number
        val_num = float_or_none(value, default=self._get_field_setting(field, 'default'))
        is_num = self._get_field_setting(field, 'convert') != 'string' and val_num is not None
        if is_num:
            value = val_num

        return ((-10, 0) if value is None
                else (1, value, 0) if not is_num  # if a field has mixed strings and numbers, strings are sorted higher
                else (0, -abs(value - limit), value - limit if reverse else limit - value) if closest
                else (0, value, 0) if not reverse and (limit is None or value <= limit)
                else (0, -value, 0) if limit is None or (reverse and value == limit) or value > limit
                else (-1, value, 0))

    def _calculate_field_preference(self, format_, field):
        type_ = self._get_field_setting(field, 'type')  # extractor, boolean, ordered, field, multiple
        get_value = lambda f: format_.get(self._get_field_setting(f, 'field'))
        if type_ == 'multiple':
            type_ = 'field'  # Only 'field' is allowed in multiple for now
            actual_fields = self._get_field_setting(field, 'field')

            value = self._get_field_setting(field, 'function')(get_value(f) for f in actual_fields)
        else:
            value = get_value(field)
        return self._calculate_field_preference_from_value(format_, field, type_, value)

    @staticmethod
    def _fill_sorting_fields(format):
        # Determine missing protocol
        if not format.get('protocol'):
            format['protocol'] = determine_protocol(format)

        # Determine missing ext
        if not format.get('ext') and 'url' in format:
            format['ext'] = determine_ext(format['url']).lower()
        if format.get('vcodec') == 'none':
            format['audio_ext'] = format['ext'] if format.get('acodec') != 'none' else 'none'
            format['video_ext'] = 'none'
        else:
            format['video_ext'] = format['ext']
            format['audio_ext'] = 'none'
        # if format.get('preference') is None and format.get('ext') in ('f4f', 'f4m'):  # Not supported?
        #    format['preference'] = -1000

        if format.get('preference') is None and format.get('ext') == 'flv' and re.match('[hx]265|he?vc?', format.get('vcodec') or ''):
            # HEVC-over-FLV is out-of-spec by FLV's original spec
            # ref. https://trac.ffmpeg.org/ticket/6389
            # ref. https://github.com/yt-dlp/yt-dlp/pull/5821
            format['preference'] = -100

        # Determine missing bitrates
        if format.get('vcodec') == 'none':
            format['vbr'] = 0
        if format.get('acodec') == 'none':
            format['abr'] = 0
        if not format.get('vbr') and format.get('vcodec') != 'none':
            format['vbr'] = try_call(lambda: format['tbr'] - format['abr']) or None
        if not format.get('abr') and format.get('acodec') != 'none':
            format['abr'] = try_call(lambda: format['tbr'] - format['vbr']) or None
        if not format.get('tbr'):
            format['tbr'] = try_call(lambda: format['vbr'] + format['abr']) or None

    def calculate_preference(self, format):
        self._fill_sorting_fields(format)
        return tuple(self._calculate_field_preference(format, field) for field in self._order)


def filesize_from_tbr(tbr, duration):
    """
    @param tbr:      Total bitrate in kbps (1000 bits/sec)
    @param duration: Duration in seconds
    @returns         Filesize in bytes
    """
    if tbr is None or duration is None:
        return None
    return int(duration * tbr * (1000 / 8))


def _request_dump_filename(url, video_id, data=None, trim_length=None):
    if data is not None:
        data = hashlib.md5(data).hexdigest()
    basen = join_nonempty(video_id, data, url, delim='_')
    trim_length = trim_length or 240
    if len(basen) > trim_length:
        h = '___' + hashlib.md5(basen.encode()).hexdigest()
        basen = basen[:trim_length - len(h)] + h
    filename = sanitize_filename(f'{basen}.dump', restricted=True)
    # Working around MAX_PATH limitation on Windows (see
    # http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx)
    if os.name == 'nt':
        absfilepath = os.path.abspath(filename)
        if len(absfilepath) > 259:
            filename = fR'\\?\{absfilepath}'
    return filename


# XXX: Temporary
class _YDLLogger:
    def __init__(self, ydl=None):
        self._ydl = ydl

    def debug(self, message):
        if self._ydl:
            self._ydl.write_debug(message)

    def info(self, message):
        if self._ydl:
            self._ydl.to_screen(message)

    def warning(self, message, *, once=False):
        if self._ydl:
            self._ydl.report_warning(message, once)

    def error(self, message, *, is_error=True):
        if self._ydl:
            self._ydl.report_error(message, is_error=is_error)

    def stdout(self, message):
        if self._ydl:
            self._ydl.to_stdout(message)

    def stderr(self, message):
        if self._ydl:
            self._ydl.to_stderr(message)



from .progress import *
