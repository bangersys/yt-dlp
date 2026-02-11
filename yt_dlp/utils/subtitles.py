import re
from .formatting import float_or_none

def parse_dfxp_time_expr(time_expr):
    """ Parses TTML/DFXP time expressions """
    if not time_expr:
        return None

    from .constants import NUMBER_RE
    mobj = re.match(rf'^(?P<time_offset>{NUMBER_RE})s?$', time_expr)
    if mobj:
        return float(mobj.group('time_offset'))

    mobj = re.match(r'^(\d+):(\d\d):(\d\d(?:(?:\.|:)\d+)?)$', time_expr)
    if mobj:
        return 3600 * int(mobj.group(1)) + 60 * int(mobj.group(2)) + float(mobj.group(3).replace(':', '.'))
    return None


def dfxp2srt(dfxp_data):
    """
    @param dfxp_data A bytes-like object containing DFXP data
    @returns A unicode object containing converted SRT data
    """
    from ..compat import compat_etree_fromstring
    from .xml import xpath_with_ns, xpath_element
    import functools
    import itertools
    import xml.etree.ElementTree

    LEGACY_NAMESPACES = (
        (b'http://www.w3.org/ns/ttml', [
            b'http://www.w3.org/2004/11/ttaf1',
            b'http://www.w3.org/2006/04/ttaf1',
            b'http://www.w3.org/2006/10/ttaf1',
        ]),
        (b'http://www.w3.org/ns/ttml#styling', [
            b'http://www.w3.org/ns/ttml#style',
        ]),
    )

    SUPPORTED_STYLING = [
        'color',
        'fontFamily',
        'fontSize',
        'fontStyle',
        'fontWeight',
        'textDecoration',
    ]

    _x = functools.partial(xpath_with_ns, ns_map={
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'ttml': 'http://www.w3.org/ns/ttml',
        'tts': 'http://www.w3.org/ns/ttml#styling',
    })

    styles = {}
    default_style = {}

    class TTMLPElementParser:
        _out = ''
        _unclosed_elements = []
        _applied_styles = []

        def start(self, tag, attrib):
            if tag in (_x('ttml:br'), 'br'):
                self._out += '\n'
            else:
                unclosed_elements = []
                style = {}
                element_style_id = attrib.get('style')
                if default_style:
                    style.update(default_style)
                if element_style_id:
                    style.update(styles.get(element_style_id, {}))
                for prop in SUPPORTED_STYLING:
                    prop_val = attrib.get(_x('tts:' + prop))
                    if prop_val:
                        style[prop] = prop_val
                if style:
                    font = ''
                    for k, v in sorted(style.items()):
                        if self._applied_styles and self._applied_styles[-1].get(k) == v:
                            continue
                        if k == 'color':
                            font += f' color="{v}"'
                        elif k == 'fontSize':
                            font += f' size="{v}"'
                        elif k == 'fontFamily':
                            font += f' face="{v}"'
                        elif k == 'fontWeight' and v == 'bold':
                            self._out += '<b>'
                            unclosed_elements.append('b')
                        elif k == 'fontStyle' and v == 'italic':
                            self._out += '<i>'
                            unclosed_elements.append('i')
                        elif k == 'textDecoration' and v == 'underline':
                            self._out += '<u>'
                            unclosed_elements.append('u')
                    if font:
                        self._out += '<font' + font + '>'
                        unclosed_elements.append('font')
                    applied_style = {}
                    if self._applied_styles:
                        applied_style.update(self._applied_styles[-1])
                    applied_style.update(style)
                    self._applied_styles.append(applied_style)
                self._unclosed_elements.append(unclosed_elements)

        def end(self, tag):
            if tag not in (_x('ttml:br'), 'br'):
                unclosed_elements = self._unclosed_elements.pop()
                for element in reversed(unclosed_elements):
                    self._out += f'</{element}>'
                if unclosed_elements and self._applied_styles:
                    self._applied_styles.pop()

        def data(self, data):
            self._out += data

        def close(self):
            return self._out.strip()

    # Fix UTF-8 encoded file wrongly marked as UTF-16. See https://github.com/yt-dlp/yt-dlp/issues/6543#issuecomment-1477169870
    # This will not trigger false positives since only UTF-8 text is being replaced
    dfxp_data = dfxp_data.replace(b'encoding=\'UTF-16\'', b'encoding=\'UTF-8\'')

    def parse_node(node):
        target = TTMLPElementParser()
        parser = xml.etree.ElementTree.XMLParser(target=target)
        parser.feed(xml.etree.ElementTree.tostring(node))
        return parser.close()

    for k, v in LEGACY_NAMESPACES:
        for ns in v:
            dfxp_data = dfxp_data.replace(ns, k)

    dfxp = compat_etree_fromstring(dfxp_data)
    out = []
    paras = dfxp.findall(_x('.//ttml:p')) or dfxp.findall('.//p')

    if not paras:
        raise ValueError('Invalid dfxp/TTML subtitle')

    repeat = False
    while True:
        for style in dfxp.findall(_x('.//ttml:style')):
            style_id = style.get('id') or style.get(_x('xml:id'))
            if not style_id:
                continue
            parent_style_id = style.get('style')
            if parent_style_id:
                if parent_style_id not in styles:
                    repeat = True
                    continue
                styles[style_id] = styles[parent_style_id].copy()
            for prop in SUPPORTED_STYLING:
                prop_val = style.get(_x('tts:' + prop))
                if prop_val:
                    styles.setdefault(style_id, {})[prop] = prop_val
        if repeat:
            repeat = False
        else:
            break

    for p in ('body', 'div'):
        ele = xpath_element(dfxp, [_x('.//ttml:' + p), './/' + p])
        if ele is None:
            continue
        style = styles.get(ele.get('style'))
        if not style:
            continue
        default_style.update(style)

    for para, index in zip(paras, itertools.count(1), strict=False):
        begin_time = parse_dfxp_time_expr(para.attrib.get('begin'))
        end_time = parse_dfxp_time_expr(para.attrib.get('end'))
        dur = parse_dfxp_time_expr(para.attrib.get('dur'))
        if begin_time is None:
            continue
        if not end_time:
            if not dur:
                continue
            end_time = begin_time + dur
        out.append('%d\n%s --> %s\n%s\n\n' % (
            index,
            srt_subtitles_timecode(begin_time),
            srt_subtitles_timecode(end_time),
            parse_node(para)))

    return ''.join(out)


def srt_subtitles_timecode(seconds):
    """ Converts seconds to SRT timecode format (HH:MM:SS,mmm) """
    from .datetime import timetuple_from_msec
    return '%02d:%02d:%02d,%03d' % timetuple_from_msec(seconds * 1000)


def ass_subtitles_timecode(seconds):
    """ Converts seconds to ASS timecode format (H:MM:SS.cc) """
    from .datetime import timetuple_from_msec
    time_ = timetuple_from_msec(seconds * 1000)
    return '%01d:%02d:%02d.%02d' % (*time_[:-1], time_.milliseconds / 10)


def subtitles_filename(filename, sub_lang, sub_format, expected_real_ext=None):
    from .filesystem import replace_extension
    return replace_extension(filename, sub_lang + '.' + sub_format, expected_real_ext)
