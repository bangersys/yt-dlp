import re



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


def lookup_unit_table(unit_table, s):
    units = '\n'.join(re.escape(u) for u in unit_table)
    mobj = re.match(r'(?P<num>[0-9]+(?:\.[0-9]*)?)\s*(?P<unit>%s)\b' % units, s)
    if not mobj:
        return None
    return parse_filesize(mobj.group('num')) * unit_table[mobj.group('unit')]


__all__ = [
    'lookup_unit_table',
    'parse_filesize',
]
