import re
import urllib.parse

from ..constants import FILE_SIZE_UNITS, NUMBER_RE, TV_PARENTAL_GUIDELINES, US_RATINGS
from .formatting import str_to_int


def lookup_unit_table(unit_table, s, strict=False):
    num_re = NUMBER_RE if strict else NUMBER_RE.replace(R'\.', '[,.]')
    units_re = '|'.join(re.escape(u) for u in unit_table)
    m = (re.fullmatch if strict else re.match)(
        rf'(?P<num>{num_re})\s*(?P<unit>{units_re})\b', s, flags=re.IGNORECASE)
    if not m:
        return None

    unit_table = {u.upper(): v for u, v in unit_table.items()}
    num = float(m.group('num').replace(',', '.'))
    mult = unit_table[m.group('unit').upper()]
    return round(num * mult)


def parse_bytes(s):
    """Parse a string indicating a byte quantity into an integer"""
    return lookup_unit_table(
        {u: 1024**i for i, u in enumerate(['', *'KMGTPEZY'])},
        s.upper(), strict=True)


def parse_filesize(s):
    if s is None:
        return None

    # The lower-case forms are of course incorrect and unofficial,
    # but we support those too

    return lookup_unit_table(FILE_SIZE_UNITS, s)


def parse_count(s):
    if s is None:
        return None

    s = re.sub(r'^[^\d]+\s', '', s).strip()

    if re.match(r'^[\d,.]+$', s):
        return str_to_int(s)

    _UNIT_TABLE = {
        'k': 1000,
        'K': 1000,
        'm': 1000 ** 2,
        'M': 1000 ** 2,
        'kk': 1000 ** 2,
        'KK': 1000 ** 2,
        'b': 1000 ** 3,
        'B': 1000 ** 3,
    }

    ret = lookup_unit_table(_UNIT_TABLE, s)
    if ret is not None:
        return ret

    mobj = re.match(r'([\d,.]+)(?:$|\s)', s)
    if mobj:
        return str_to_int(mobj.group(1))


def parse_resolution(s, *, lenient=False):
    if s is None:
        return {}

    if lenient:
        mobj = re.search(r'(?P<w>\d+)\s*[xX×,]\s*(?P<h>\d+)', s)
    else:
        mobj = re.search(r'(?<![a-zA-Z0-9])(?P<w>\d+)\s*[xX×,]\s*(?P<h>\d+)(?![a-zA-Z0-9])', s)
    if mobj:
        return {
            'width': int(mobj.group('w')),
            'height': int(mobj.group('h')),
        }

    mobj = re.search(r'(?<![a-zA-Z0-9])(\d+)[pPiI](?![a-zA-Z0-9])', s)
    if mobj:
        return {'height': int(mobj.group(1))}

    mobj = re.search(r'\b([48])[kK]\b', s)
    if mobj:
        return {'height': int(mobj.group(1)) * 540}

    if lenient:
        mobj = re.search(r'(?<!\d)(\d{2,5})w(?![a-zA-Z0-9])', s)
        if mobj:
            return {'width': int(mobj.group(1))}

    return {}


def parse_bitrate(s):
    if not isinstance(s, str):
        return
    mobj = re.search(r'\b(\d+)\s*kbps', s)
    if mobj:
        return int(mobj.group(1))


def parse_qs(url, **kwargs):
    return urllib.parse.parse_qs(urllib.parse.urlparse(url).query, **kwargs)


def parse_age_limit(s):
    # isinstance(False, int) is True. So type() must be used instead
    if type(s) is int:  # noqa: E721
        return s if 0 <= s <= 21 else None
    elif not isinstance(s, str):
        return None
    m = re.match(r'^(?P<age>\d{1,2})\+?$', s)
    if m:
        return int(m.group('age'))
    s = s.upper()
    if s in US_RATINGS:
        return US_RATINGS[s]
    m = re.match(r'^TV[_-]?({})$'.format('|'.join(k[3:] for k in TV_PARENTAL_GUIDELINES)), s)
    if m:
        return TV_PARENTAL_GUIDELINES['TV-' + m.group(1)]
    return None
