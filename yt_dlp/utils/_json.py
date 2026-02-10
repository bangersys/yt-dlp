import contextlib
import json
import os
import re
import sys
import tempfile
import urllib.parse

from ..constants import JSON_LD_RE, NO_DEFAULT


def write_json_file(obj, fn):
    """Encode obj as JSON and write it to fn, atomically if possible."""
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


class LenientJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, transform_source=None, ignore_extra=False, close_objects=0, **kwargs):
        self.transform_source, self.ignore_extra = transform_source, ignore_extra
        self._close_attempts = 2 * close_objects
        super().__init__(*args, **kwargs)

    @staticmethod
    def _close_object(err):
        doc = err.doc[:err.pos]
        # We need to add comma first to get the correct error message
        if err.msg.startswith("Expecting ','"):
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


def strip_jsonp(code):
    return re.sub(
        r'''(?sx)^
            (?:window\.)?(?P<func_name>[a-zA-Z0-9_.$]*)
            (?:\s*&&\s*(?P=func_name))?
            \s*\(\s*(?P<callback_data>.*)\);?
            \s*?(?://[^
]*)*$''',
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


def smuggle_url(url, data):
    """Pass additional data in a URL for internal use."""
    url, idata = unsmuggle_url(url, {})
    data.update(idata)
    sdata = urllib.parse.urlencode(
        {'__youtubedl_smuggle': json.dumps(data)})
    return url + '#' + sdata


def unsmuggle_url(smug_url, default=None):
    if '#__youtubedl_smuggle' not in smug_url:
        return smug_url, default
    url, _, sdata = smug_url.rpartition('#')
    jsond_list = urllib.parse.parse_qs(sdata).get('__youtubedl_smuggle')
    if not jsond_list:
        return smug_url, default
    try:
        data = json.loads(jsond_list[0])
    except (json.JSONDecodeError, TypeError, IndexError):
        return smug_url, default
    return url, data


def jwt_json_bytes(obj):
    return json.dumps(obj, separators=(',', ':')).encode()


def search_json(start_pattern, string, name, video_id=None, *, end_pattern='',
                contains_pattern=r'{(?s:.+)}', fatal=True, default=NO_DEFAULT, **kwargs):
    has_default = default is not NO_DEFAULT
    pattern = rf'(?:{start_pattern})\s*(?P<json>{contains_pattern})\s*(?:{end_pattern})'
    mobj = re.search(pattern, string, flags=re.DOTALL | re.IGNORECASE)
    if not mobj:
        if has_default:
            return default
        if fatal:
            raise ValueError(f'Unable to extract {name}')
        return None

    json_string = mobj.group('json')
    transform_source = kwargs.pop('transform_source', None)
    if transform_source:
        json_string = transform_source(json_string)

    try:
        return json.loads(json_string, cls=LenientJSONDecoder, **kwargs)
    except (json.JSONDecodeError, TypeError, ValueError) as err:
        if has_default:
            return default
        if fatal:
            raise ValueError(f'Failed to parse {name} JSON: {err}')
        return None


def yield_json_ld(html):
    for m in re.finditer(JSON_LD_RE, html):
        json_ld = m.group('json_ld')
        try:
            yield json.loads(json_ld, cls=LenientJSONDecoder)
        except json.JSONDecodeError:
            continue


def search_nextjs_data(webpage, video_id, *, fatal=True, default=NO_DEFAULT, **kwargs):
    return search_json(
        r'<script[^>]+id=[\'\"]__NEXT_DATA__[\'\"][^>]*>', webpage, 'next.js data',
        video_id, end_pattern='</script>', fatal=fatal, default=default, **kwargs)


def search_nextjs_v13_data(webpage, video_id, fatal=True):
    nextjs_data = {}
    if not isinstance(webpage, str):
        return nextjs_data

    # Avoid circular imports at module init
    from ._utils import try_call

    def flatten(flight_data):
        if not isinstance(flight_data, list):
            return
        if len(flight_data) == 4 and flight_data[0] == '$':
            _, name, _, data = flight_data
            if not isinstance(data, dict):
                return
            children = data.pop('children', None)
            if data and isinstance(name, str) and re.fullmatch(r'\$L[0-9a-f]+', name):
                nextjs_data[name[2:]] = data
            flatten(children)
            return
        for f in flight_data:
            flatten(f)

    flight_text = ''
    for flight_segment in re.findall(r'<script\b[^>]*>self\.__next_f\.push\((\[.+?\])\)</script>', webpage):
        segment = json.loads(flight_segment, cls=LenientJSONDecoder) if fatal else try_call(
            lambda: json.loads(flight_segment, cls=LenientJSONDecoder))
        if not isinstance(segment, list) or len(segment) != 2:
            continue
        payload_type, chunk = segment
        if payload_type == 1:
            flight_text += chunk

    for f in flight_text.splitlines():
        prefix, _, body = f.lstrip().partition(':')
        if not re.fullmatch(r'[0-9a-f]+', prefix):
            continue
        if body.startswith('[') and body.endswith(']'):
            flatten(json.loads(body, cls=LenientJSONDecoder) if fatal else try_call(
                lambda: json.loads(body, cls=LenientJSONDecoder)))
        elif body.startswith('{') and body.endswith('}'):
            data = json.loads(body, cls=LenientJSONDecoder) if fatal else try_call(
                lambda: json.loads(body, cls=LenientJSONDecoder))
            if data is not None:
                nextjs_data[prefix] = data

    return nextjs_data


def search_nuxt_data(webpage, video_id, context_name='__NUXT__', *, fatal=True, traverse=('data', 0)):
    rectx = re.escape(context_name)
    function_re = r'\(function\((?P<arg_keys>.*?)\){.*?\breturn\s+(?P<js>{.*?})\s*;?\s*}\((?P<arg_vals>.*?)\)'
    mobj = re.search(
        rf'<script>\s*window\.{rectx}={function_re}\s*\)\s*;?\s*</script>|{rectx}\(.*?{function_re}',
        webpage)

    if not mobj:
        if fatal:
            raise ValueError(f'Unable to extract {context_name}')
        return {}

    js = mobj.group('js')
    arg_keys = mobj.group('arg_keys')
    arg_vals = mobj.group('arg_vals')

    try:
        args_list = json.loads(f'[{arg_vals}]', cls=LenientJSONDecoder)
        args = dict(zip(arg_keys.split(','), map(json.dumps, args_list), strict=True))
        ret = json.loads(js, transform_source=lambda s: js_to_json(s, vars=args), cls=LenientJSONDecoder)
        from .traversal import traverse_obj
        return traverse_obj(ret, traverse) or {}
    except Exception:
        if fatal:
            raise
        return {}


def resolve_nuxt_array(array, video_id, *, fatal=True, default=NO_DEFAULT):
    from .jslib import devalue

    if default is not NO_DEFAULT:
        fatal = False

    if not isinstance(array, list) or not array:
        if fatal:
            raise ValueError('Invalid Nuxt JSON data')
        return {} if default is NO_DEFAULT else default

    def indirect_reviver(data):
        return data

    def json_reviver(data):
        return json.loads(data)

    gen = devalue.parse_iter(array, revivers={
        'NuxtError': indirect_reviver,
        'EmptyShallowRef': json_reviver,
        'EmptyRef': json_reviver,
        'ShallowRef': indirect_reviver,
        'ShallowReactive': indirect_reviver,
        'Ref': indirect_reviver,
        'Reactive': indirect_reviver,
    })

    while True:
        try:
            error_msg = gen.send(None)
            if fatal:
                raise ValueError(f'Error resolving Nuxt JSON: {error_msg}')
        except StopIteration as error:
            return error.value or ({} if default is NO_DEFAULT else default)


def search_nuxt_json(webpage, video_id, *, fatal=True, default=NO_DEFAULT):
    array = search_json(
        r'<script\b[^>]+\bid="__NUXT_DATA__"[^>]*>', webpage,
        'Nuxt JSON data', video_id, contains_pattern=r'\[(?s:.*?)\]',
        fatal=fatal, default=default, end_pattern=r'\s*</script>')

    if not array:
        return default if default is not NO_DEFAULT else {}

    return resolve_nuxt_array(array, video_id, fatal=fatal, default=default)
