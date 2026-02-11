import calendar
import collections
import contextlib
import datetime as dt
import email.utils
import functools
import inspect
import re
import time

from ..compat import compat_datetime_from_timestamp
from ..constants import (
    DATE_FORMATS_DAY_FIRST,
    DATE_FORMATS_MONTH_FIRST,
    ENGLISH_MONTH_NAMES,
    MONTH_NAMES,
    NO_DEFAULT,
    NUMBER_RE,
    TIMEZONE_NAMES,
)

_timetuple = collections.namedtuple('Time', ('hours', 'minutes', 'seconds', 'milliseconds'))


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


def timetuple_from_msec(msec):
    secs, msec = divmod(msec, 1000)
    mins, secs = divmod(secs, 60)
    hrs, mins = divmod(mins, 60)
    return _timetuple(hrs, mins, secs, msec)


def formatSeconds(secs, delim=':', msec=False):
    time_tuple = timetuple_from_msec(secs * 1000)
    if time_tuple.hours:
        ret = '%d%s%02d%s%02d' % (time_tuple.hours, delim, time_tuple.minutes, delim, time_tuple.seconds)
    elif time_tuple.minutes:
        ret = '%d%s%02d' % (time_tuple.minutes, delim, time_tuple.seconds)
    else:
        ret = '%d' % time_tuple.seconds
    return '%s.%03d' % (ret, time_tuple.milliseconds) if msec else ret


def extract_timezone(date_str, default=None):
    m = re.search(
        r'''(?x)
            ^.{8,}?                                              # >=8 char non-TZ prefix, if present
            (?P<tz>Z|                                            # just the UTC Z, or
                (?:(?<=.\b\d{4}|\b\d{2}:\d\d)|                   # preceded by 4 digits or hh:mm or
                   (?<!.\b[a-zA-Z]{3}|[a-zA-Z]{4}|..\b\d\d))     # not preceded by 3 alpha word or >= 4 alpha or 2 digits
                   [ ]?                                          # optional space
                (?P<sign>\+|-)                                   # +/-
                (?P<hours>[0-9]{2}):?(?P<minutes>[0-9]{2})       # hh[:]mm
            $)
        ''', date_str)
    timezone = None

    if not m:
        m = re.search(r'\d{1,2}:\d{1,2}(?:\.\d+)?(?P<tz>\s*[A-Z]+)$', date_str)
        timezone = TIMEZONE_NAMES.get(m and m.group('tz').strip())
        if timezone is not None:
            date_str = date_str[:-len(m.group('tz'))]
            timezone = dt.timedelta(hours=timezone)
    else:
        date_str = date_str[:-len(m.group('tz'))]
        if m.group('sign'):
            sign = 1 if m.group('sign') == '+' else -1
            timezone = dt.timedelta(
                hours=sign * int(m.group('hours')),
                minutes=sign * int(m.group('minutes')))

    if timezone is None and default is not NO_DEFAULT:
        timezone = default or dt.timedelta()

    return timezone, date_str


@partial_application
def parse_iso8601(date_str, delimiter='T', timezone=None):
    """ Return a UNIX timestamp from the given date """

    if date_str is None:
        return None

    date_str = re.sub(r'\.[0-9]+', '', date_str)

    timezone, date_str = extract_timezone(date_str, timezone)

    with contextlib.suppress(ValueError, TypeError):
        date_format = f'%Y-%m-%d{delimiter}%H:%M:%S'
        dt_ = dt.datetime.strptime(date_str, date_format) - timezone
        return calendar.timegm(dt_.timetuple())


def date_formats(day_first=True):
    return DATE_FORMATS_DAY_FIRST if day_first else DATE_FORMATS_MONTH_FIRST


def unified_strdate(date_str, day_first=True):
    """Return a string with the date in the format YYYYMMDD"""

    if date_str is None:
        return None
    upload_date = None
    date_str = date_str.replace(',', ' ')
    date_str = re.sub(r'(?i)\s*(?:AM|PM)(?:\s+[A-Z]+)?', '', date_str)
    _, date_str = extract_timezone(date_str)

    for expression in date_formats(day_first):
        with contextlib.suppress(ValueError):
            upload_date = dt.datetime.strptime(date_str, expression).strftime('%Y%m%d')
    if upload_date is None:
        timetuple = email.utils.parsedate_tz(date_str)
        if timetuple:
            with contextlib.suppress(ValueError):
                upload_date = dt.datetime(*timetuple[:6]).strftime('%Y%m%d')
    if upload_date is not None:
        return str(upload_date)


@partial_application
def unified_timestamp(date_str, day_first=True, tz_offset=0):
    if not isinstance(date_str, str):
        return None

    date_str = re.sub(r'\s+', ' ', re.sub(
        r'(?i)[,|]|(mon|tues?|wed(nes)?|thu(rs)?|fri|sat(ur)?|sun)(day)?', '', date_str))

    pm_delta = 12 if re.search(r'(?i)PM', date_str) else 0
    timezone, date_str = extract_timezone(
        date_str, default=dt.timedelta(hours=tz_offset) if tz_offset else NO_DEFAULT)

    date_str = re.sub(r'(?i)\s*(?:AM|PM)(?:\s+[A-Z]+)?', '', date_str)

    m = re.search(r'\d{1,2}:\d{1,2}(?:\.\d+)?(?P<tz>\s*[A-Z]+)$', date_str)
    if m:
        date_str = date_str[:-len(m.group('tz'))]

    m = re.search(r'^([0-9]{4,}-[0-9]{1,2}-[0-9]{1,2}T[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}\.[0-9]{6})[0-9]+$', date_str)
    if m:
        date_str = m.group(1)

    for expression in date_formats(day_first):
        with contextlib.suppress(ValueError):
            dt_ = dt.datetime.strptime(date_str, expression) - (timezone or dt.timedelta()) + dt.timedelta(hours=pm_delta)
            return calendar.timegm(dt_.timetuple())

    timetuple = email.utils.parsedate_tz(date_str)
    if timetuple:
        return calendar.timegm(timetuple) + pm_delta * 3600 - int((timezone or dt.timedelta()).total_seconds())


def datetime_from_str(date_str, precision='auto', format='%Y%m%d'):
    R"""
    Return a datetime object from a string.
    Supported format:
        (now|today|yesterday|DATE)([+-]\d+(microsecond|second|minute|hour|day|week|month|year)s?)?
    """
    auto_precision = False
    if precision == 'auto':
        auto_precision = True
        precision = 'microsecond'
    today = datetime_round(dt.datetime.now(dt.timezone.utc), precision)
    if date_str in ('now', 'today'):
        return today
    if date_str == 'yesterday':
        return today - dt.timedelta(days=1)
    match = re.match(
        r'(?P<start>.+)(?P<sign>[+-])(?P<time>\d+)(?P<unit>microsecond|second|minute|hour|day|week|month|year)s?',
        date_str)
    if match is not None:
        start_time = datetime_from_str(match.group('start'), precision, format)
        time_delta = int(match.group('time')) * (-1 if match.group('sign') == '-' else 1)
        unit = match.group('unit')
        if unit == 'month' or unit == 'year':
            new_date = datetime_add_months(start_time, time_delta * 12 if unit == 'year' else time_delta)
            unit = 'day'
        else:
            if unit == 'week':
                unit = 'day'
                time_delta *= 7
            delta = dt.timedelta(**{unit + 's': time_delta})
            new_date = start_time + delta
        if auto_precision:
            return datetime_round(new_date, unit)
        return new_date

    return datetime_round(dt.datetime.strptime(date_str, format), precision)


def date_from_str(date_str, format='%Y%m%d', strict=False):
    R"""Return a date object from a string using datetime_from_str."""
    if strict and not re.fullmatch(r'\d{8}|(now|today|yesterday)(-\d+(day|week|month|year)s?)?', date_str):
        raise ValueError(f'Invalid date format "{date_str}"')
    return datetime_from_str(date_str, precision='microsecond', format=format).date()


def datetime_add_months(dt_, months):
    """Increment/Decrement a datetime object by months."""
    month = dt_.month + months - 1
    year = dt_.year + month // 12
    month = month % 12 + 1
    day = min(dt_.day, calendar.monthrange(year, month)[1])
    return dt_.replace(year, month, day)


def datetime_round(dt_, precision='day'):
    if precision == 'microsecond':
        return dt_

    time_scale = 1_000_000
    unit_seconds = {
        'day': 86400,
        'hour': 3600,
        'minute': 60,
        'second': 1,
    }
    roundto = lambda x, n: ((x + n / 2) // n) * n
    timestamp = roundto(calendar.timegm(dt_.timetuple()) + dt_.microsecond / time_scale, unit_seconds[precision])
    return compat_datetime_from_timestamp(timestamp)


def hyphenate_date(date_str):
    match = re.match(r'^(\d\d\d\d)(\d\d)(\d\d)$', date_str)
    if match is not None:
        return '-'.join(match.groups())
    return date_str


class DateRange:
    """Represents a time interval between two dates"""

    def __init__(self, start=None, end=None):
        if start is not None:
            self.start = date_from_str(start, strict=True)
        else:
            self.start = dt.datetime.min.date()
        if end is not None:
            self.end = date_from_str(end, strict=True)
        else:
            self.end = dt.datetime.max.date()
        if self.start > self.end:
            raise ValueError(f'Date range: "{self}" , the start date must be before the end date')

    @classmethod
    def day(cls, day):
        return cls(day, day)

    def __contains__(self, date):
        if not isinstance(date, dt.date):
            date = date_from_str(date)
        return self.start <= date <= self.end

    def __repr__(self):
        return f'{__name__}.{type(self).__name__}({self.start.isoformat()!r}, {self.end.isoformat()!r})'

    def __str__(self):
        return f'{self.start} to {self.end}'

    def __eq__(self, other):
        return (isinstance(other, DateRange)
                and self.start == other.start and self.end == other.end)


def month_by_name(name, lang='en'):
    month_names = MONTH_NAMES.get(lang, MONTH_NAMES['en'])
    try:
        return month_names.index(name) + 1
    except ValueError:
        return None


def month_by_abbreviation(abbrev):
    try:
        return [s[:3] for s in ENGLISH_MONTH_NAMES].index(abbrev) + 1
    except ValueError:
        return None


def strftime_or_none(timestamp, date_format='%Y%m%d', default=None):
    datetime_object = None
    try:
        if isinstance(timestamp, (int, float)):
            datetime_object = dt.datetime.fromtimestamp(timestamp, dt.timezone.utc)
        elif isinstance(timestamp, str):
            datetime_object = dt.datetime.strptime(timestamp, '%Y%m%d')
        if datetime_object is None:
            return default
        date_format = re.sub(r'(?<!%)(%%)*%s', rf'\g<1>{int(datetime_object.timestamp())}', date_format)
        return datetime_object.strftime(date_format)
    except (ValueError, TypeError, AttributeError, OverflowError, OSError):
        return default


def parse_duration(s):
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None

    days, hours, mins, secs, ms = [None] * 5
    m = re.match(r'''(?x)
            (?P<before_secs>
                (?:(?:(?P<days>[0-9]+):)?(?P<hours>[0-9]+):)?(?P<mins>[0-9]+):)?
            (?P<secs>(?(before_secs)[0-9]{1,2}|[0-9]+))
            (?P<ms>[.:][0-9]+)?Z?$
        ''', s)
    if m:
        days, hours, mins, secs, ms = m.group('days', 'hours', 'mins', 'secs', 'ms')
    else:
        m = re.match(
            r'''(?ix)(?:P?
                (?:
                    [0-9]+\s*y(?:ears?)?,?\s*
                )?
                (?:
                    [0-9]+\s*m(?:onths?)?,?\s*
                )?
                (?:
                    [0-9]+\s*w(?:eeks?)?,?\s*
                )?
                (?:
                    (?P<days>[0-9]+)\s*d(?:ays?)?,?\s*
                )?
                T)?
                (?:
                    (?P<hours>[0-9]+)\s*h(?:(?:ou)?rs?)?,?\s*
                )?
                (?:
                    (?P<mins>[0-9]+)\s*m(?:in(?:ute)?s?)?,?\s*
                )?
                (?:
                    (?P<secs>[0-9]+)(?P<ms>\.[0-9]+)?\s*s(?:ec(?:ond)?s?)?\s*
                )?Z?$''', s)
        if m:
            days, hours, mins, secs, ms = m.groups()
        else:
            m = re.match(r'(?i)(?:(?P<hours>[0-9.]+)\s*(?:hours?)|(?P<mins>[0-9.]+)\s*(?:mins?\.?|minutes?)\s*)Z?$', s)
            if m:
                hours, mins = m.groups()
            else:
                return None

    if ms:
        ms = ms.replace(':', '.')
    return sum(float(part or 0) * mult for part, mult in (
        (days, 86400), (hours, 3600), (mins, 60), (secs, 1), (ms, 1)))


def parse_dfxp_time_expr(time_expr):
    if not time_expr:
        return None

    mobj = re.match(rf'^(?P<time_offset>{NUMBER_RE})s?$', time_expr)
    if mobj:
        return float(mobj.group('time_offset'))

    mobj = re.match(r'^(\d+):(\d\d):(\d\d(?:(?:\.|:)\d+)?)$', time_expr)
    if mobj:
        return 3600 * int(mobj.group(1)) + 60 * int(mobj.group(2)) + float(mobj.group(3).replace(':', '.'))
    return None


def srt_subtitles_timecode(seconds):
    return '%02d:%02d:%02d,%03d' % timetuple_from_msec(seconds * 1000)


def ass_subtitles_timecode(seconds):
    time_tuple = timetuple_from_msec(seconds * 1000)
    return '%01d:%02d:%02d.%02d' % (*time_tuple[:-1], time_tuple.milliseconds / 10)


def time_seconds(**kwargs):
    return time.time() + dt.timedelta(**kwargs).total_seconds()


__all__ = [
    'DateRange',
    'ass_subtitles_timecode',
    'date_formats',
    'date_from_str',
    'datetime_add_months',
    'datetime_from_str',
    'datetime_round',
    'extract_timezone',
    'formatSeconds',
    'hyphenate_date',
    'month_by_abbreviation',
    'month_by_name',
    'parse_dfxp_time_expr',
    'parse_duration',
    'parse_iso8601',
    'srt_subtitles_timecode',
    'strftime_or_none',
    'time_seconds',
    'timeconvert',
    'timetuple_from_msec',
    'unified_strdate',
    'unified_timestamp',
]


def timeconvert(timestr):
    """Convert RFC 2822 defined time string into system timestamp"""
    timestamp = None
    timetuple = email.utils.parsedate_tz(timestr)
    if timetuple is not None:
        timestamp = email.utils.mktime_tz(timetuple)
    return timestamp
