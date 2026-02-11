
import codecs
import re


def uppercase_escape(s):
    unicode_escape = codecs.getdecoder('unicode_escape')
    return re.sub(
        r'\\U[0-9a-fA-F]{8}',
        lambda m: unicode_escape(m.group(0))[0],
        s)


def lowercase_escape(s):
    unicode_escape = codecs.getdecoder('unicode_escape')
    return re.sub(
        r'\\u[0-9a-fA-F]{4}',
        lambda m: unicode_escape(m.group(0))[0],
        s)


def limit_length(s, length):
    """ Add ellipses to overly long strings """
    if s is None:
        return None
    ELLIPSES = '...'
    if len(s) > length:
        return s[:length - len(ELLIPSES)] + ELLIPSES
    return s
