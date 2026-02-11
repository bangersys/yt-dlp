import functools
import os
import platform
import re
from .constants import NUMBER_RE


def _base_n_table(n, table):
    """Internal helper for base-n conversion"""
    if not table and not n:
        raise ValueError('Either table or n must be specified')
    table = (table or '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')[:n]

    if n and n != len(table):
        raise ValueError(f'base {n} exceeds table length {len(table)}')
    return table


def encode_base_n(num, n=None, table=None):
    """Convert given int to a base-n string"""
    table = _base_n_table(n, table)
    if not num:
        return table[0]

    result, base = '', len(table)
    while num:
        result = table[num % base] + result
        num = num // base
    return result


def decode_base_n(string, n=None, table=None):
    """Convert given base-n string to int"""
    table = {char: index for index, char in enumerate(_base_n_table(n, table))}
    result, base = 0, len(table)
    for char in string:
        result = result * base + table[char]
    return result


def decode_packed_codes(code):
    """
    Research Note: Decodes Dean Edwards' Packer encoded JavaScript.
    Commonly seen in web players.
    """
    mobj = re.search(r'}?\(["\'](.+)["\'],\s*(\d+),\s*(\d+),\s*["\'](.+)["\']\.split\([\'"]\|[\'"]\)', code)
    if not mobj:
        return code
    
    p, a, c, k = mobj.groups()
    a = int(a)
    c = int(c)
    k = k.split('|')

    def e(c):
        res = ''
        if c >= a:
            res += e(c // a)
        c %= a
        if c > 35:
            res += chr(c + 29)
        else:
            res += chr(c + (48 if c < 10 else 87))
        return res

    while c:
        c -= 1
        if k[c]:
            code = re.sub(fr'\b{e(c)}\b', k[c], code)
    return code


def lookup_unit_table(unit_table, s, strict=False):
    num_re = NUMBER_RE if strict else NUMBER_RE.replace(R'\.', '[,.]')
    units_re = '|'.join(re.escape(u) for u in unit_table)
    m = (re.fullmatch if strict else re.match)(
        rf'(?P<num>{num_re})\s*(?P<unit>{units_re})\b', s)
    if not m:
        return None

    num = float(m.group('num').replace(',', '.'))
    mult = unit_table[m.group('unit')]
    return round(num * mult)


from .formatting import int_or_none


def version_tuple(v, *, lenient=False):
    parse = int_or_none(default=-1) if lenient else int
    return tuple(parse(e) for e in re.split(r'[-.]', v))


@functools.cache
def get_windows_version():
    """ Get Windows version. returns () if it's not running on Windows """
    if os.name == 'nt':
        return version_tuple(platform.win32_ver()[1])
    else:
        return ()


def parse_filesize(s):
    if s is None:
        return None

    # The lower-case forms are of course not metric but they are used in the wild
    # (e.g. by PolskieRadio)
    UNIT_TABLE = {
        'k': 1000,
        'K': 1000,
        'Kb': 1000,
        'Ki': 1024,
        'KiB': 1024,
        'kB': 1000,
        'KB': 1000,
        'm': 1000**2,
        'M': 1000**2,
        'Mb': 1000**2,
        'Mi': 1024**2,
        'MiB': 1024**2,
        'MB': 1000**2,
        'g': 1000**3,
        'G': 1000**3,
        'Gb': 1000**3,
        'Gi': 1024**3,
        'GiB': 1024**3,
        'GB': 1000**3,
        't': 1000**4,
        'T': 1000**4,
        'Tb': 1000**4,
        'Ti': 1024**4,
        'TiB': 1024**4,
        'TB': 1000**4,
        'p': 1000**5,
        'P': 1000**5,
        'Pb': 1000**5,
        'Pi': 1024**5,
        'PiB': 1024**5,
        'PB': 1000**5,
        'e': 1000**6,
        'E': 1000**6,
        'Eb': 1000**6,
        'Ei': 1024**6,
        'EiB': 1024**6,
        'EB': 1000**6,
        'z': 1000**7,
        'Z': 1000**7,
        'Zb': 1000**7,
        'Zi': 1024**7,
        'ZiB': 1024**7,
        'ZB': 1000**7,
        'y': 1000**8,
        'Y': 1000**8,
        'Yb': 1000**8,
        'Yi': 1024**8,
        'YiB': 1024**8,
        'YB': 1000**8,
    }

    units = '\n'.join(re.escape(u) for u in UNIT_TABLE)
    mobj = re.match(r'(?P<num>[0-9]+(?:\.[0-9]*)?)\s*(?P<unit>%s)\b' % units, s)
    if mobj:
        return parse_filesize(mobj.group('num')) * UNIT_TABLE[mobj.group('unit')]

    mobj = re.match(r'(?P<num>[0-9]+(?:\.[0-9]*)?)\b', s)
    if mobj:
        return int(float(mobj.group('num')))

    return None
