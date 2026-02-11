from __future__ import annotations

import base64
import codecs
import collections
import collections.abc
import functools
import inspect
import json
import random
import re
import typing
import urllib.parse
import urllib.request

if typing.TYPE_CHECKING:
    T = typing.TypeVar('T')

from ..constants import CHROME_MAJOR_VERSION_RANGE, USER_AGENT_TMPL
from .json import NO_DEFAULT
from .formatting import format_field, remove_start



def random_user_agent():
    return USER_AGENT_TMPL.format(f'{random.randint(*CHROME_MAJOR_VERSION_RANGE)}.0.0.0')


class HTTPHeaderDict(dict):
    """
    Store and access keys case-insensitively.
    The constructor can take multiple dicts, in which keys in the latter are prioritised.

    Retains a case sensitive mapping of the headers, which can be accessed via `.sensitive()`.
    """
    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> typing.Self:
        obj = dict.__new__(cls, *args, **kwargs)
        obj.__sensitive_map = {}
        return obj

    def __init__(self, /, *args, **kwargs):
        super().__init__()
        self.__sensitive_map = {}

        for dct in filter(None, args):
            self.update(dct)
        if kwargs:
            self.update(kwargs)

    def sensitive(self, /) -> dict[str, str]:
        return {
            self.__sensitive_map[key]: value
            for key, value in self.items()
        }

    def __contains__(self, key: str, /) -> bool:
        return super().__contains__(key.title() if isinstance(key, str) else key)

    def __delitem__(self, key: str, /) -> None:
        key = key.title()
        del self.__sensitive_map[key]
        super().__delitem__(key)

    def __getitem__(self, key, /) -> str:
        return super().__getitem__(key.title())

    def __ior__(self, other, /):
        if isinstance(other, type(self)):
            other = other.sensitive()
        if isinstance(other, dict):
            self.update(other)
            return
        return NotImplemented

    def __or__(self, other, /) -> typing.Self:
        if isinstance(other, type(self)):
            other = other.sensitive()
        if isinstance(other, dict):
            return type(self)(self.sensitive(), other)
        return NotImplemented

    def __ror__(self, other, /) -> typing.Self:
        if isinstance(other, type(self)):
            other = other.sensitive()
        if isinstance(other, dict):
            return type(self)(other, self.sensitive())
        return NotImplemented

    def __setitem__(self, key: str, value, /) -> None:
        if isinstance(value, bytes):
            value = value.decode('latin-1')
        key_title = key.title()
        self.__sensitive_map[key_title] = key
        super().__setitem__(key_title, str(value).strip())

    def clear(self, /) -> None:
        self.__sensitive_map.clear()
        super().clear()

    def copy(self, /) -> typing.Self:
        return type(self)(self.sensitive())

    @typing.overload
    def get(self, key: str, /) -> str | None: ...

    @typing.overload
    def get(self, key: str, /, default: T) -> str | T: ...

    def get(self, key, /, default=NO_DEFAULT):
        key = key.title()
        if default is NO_DEFAULT:
            return super().get(key)
        return super().get(key, default)

    @typing.overload
    def pop(self, key: str, /) -> str: ...

    @typing.overload
    def pop(self, key: str, /, default: T) -> str | T: ...

    def pop(self, key, /, default=NO_DEFAULT):
        key = key.title()
        if default is NO_DEFAULT:
            self.__sensitive_map.pop(key)
            return super().pop(key)
        self.__sensitive_map.pop(key, default)
        return super().pop(key, default)

    def popitem(self) -> tuple[str, str]:
        self.__sensitive_map.popitem()
        return super().popitem()

    @typing.overload
    def setdefault(self, key: str, /) -> str: ...

    @typing.overload
    def setdefault(self, key: str, /, default) -> str: ...

    def setdefault(self, key, /, default=None) -> str:
        key = key.title()
        if key in self.__sensitive_map:
            return super().__getitem__(key)

        self[key] = default or ''
        return self[key]

    def update(self, other, /, **kwargs) -> None:
        if isinstance(other, type(self)):
            other = other.sensitive()
        if isinstance(other, collections.abc.Mapping):
            for key, value in other.items():
                self[key] = value

        elif hasattr(other, 'keys'):
            for key in other.keys():  # noqa: SIM118
                self[key] = other[key]

        else:
            for key, value in other:
                self[key] = value

        for key, value in kwargs.items():
            self[key] = value


std_headers = HTTPHeaderDict({
    'User-Agent': random_user_agent(),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
    'Sec-Fetch-Mode': 'navigate',
})


def clean_proxies(proxies: dict, headers: HTTPHeaderDict):
    req_proxy = headers.pop('Ytdl-Request-Proxy', None)
    if req_proxy:
        proxies.clear()  # XXX: compat: Ytdl-Request-Proxy takes preference over everything, including NO_PROXY
        proxies['all'] = req_proxy
    for proxy_key, proxy_url in proxies.items():
        if proxy_url == '__noproxy__':
            proxies[proxy_key] = None
            continue
        if proxy_key == 'no':  # special case
            continue
        if proxy_url is not None:
            # Ensure proxies without a scheme are http.
            try:
                proxy_scheme = urllib.request._parse_proxy(proxy_url)[0]
            except ValueError:
                # Ignore invalid proxy URLs. Sometimes these may be introduced through environment
                # variables unrelated to proxy settings - e.g. Colab `COLAB_LANGUAGE_SERVER_PROXY`.
                # If the proxy is going to be used, the Request Handler proxy validation will handle it.
                continue
            if proxy_scheme is None:
                proxies[proxy_key] = 'http://' + remove_start(proxy_url, '//')

            replace_scheme = {
                'socks5': 'socks5h',  # compat: socks5 was treated as socks5h
                'socks': 'socks4',  # compat: non-standard
            }
            if proxy_scheme in replace_scheme:
                proxies[proxy_key] = urllib.parse.urlunparse(
                    urllib.parse.urlparse(proxy_url)._replace(scheme=replace_scheme[proxy_scheme]))


def clean_headers(headers: HTTPHeaderDict):
    if 'Youtubedl-No-Compression' in headers:  # compat
        del headers['Youtubedl-No-Compression']
        headers['Accept-Encoding'] = 'identity'
    headers.pop('Ytdl-socks-proxy', None)


def remove_dot_segments(path):
    # Implements RFC3986 5.2.4 remote_dot_segments
    # Pseudo-code: https://tools.ietf.org/html/rfc3986#section-5.2.4
    # https://github.com/urllib3/urllib3/blob/ba49f5c4e19e6bca6827282feb77a3c9f937e64b/src/urllib3/util/url.py#L263
    output = []
    segments = path.split('/')
    for s in segments:
        if s == '.':
            continue
        elif s == '..':
            if output:
                output.pop()
        else:
            output.append(s)
    if not segments[0] and (not output or output[0]):
        output.insert(0, '')
    if segments[-1] in ('.', '..'):
        output.append('')
    return '/'.join(output)


def escape_rfc3986(s):
    """Escape non-ASCII characters as suggested by RFC 3986"""
    return urllib.parse.quote(s, b"%/;:@&=+$,!~*'()?#[]")


def normalize_url(url):
    """Normalize URL as suggested by RFC 3986"""
    url_parsed = urllib.parse.urlparse(url)
    return url_parsed._replace(
        netloc=url_parsed.netloc.encode('idna').decode('ascii'),
        path=escape_rfc3986(remove_dot_segments(url_parsed.path)),
        params=escape_rfc3986(url_parsed.params),
        query=escape_rfc3986(url_parsed.query),
        fragment=escape_rfc3986(url_parsed.fragment),
    ).geturl()


def select_proxy(url, proxies):
    """Unified proxy selector for all backends"""
    url_components = urllib.parse.urlparse(url)
    if 'no' in proxies:
        hostport = url_components.hostname + format_field(url_components.port, None, ':%s')
        if urllib.request.proxy_bypass_environment(hostport, {'no': proxies['no']}):
            return
        elif urllib.request.proxy_bypass(hostport):  # check system settings
            return

    from .traversal import traverse_obj
    return traverse_obj(proxies, url_components.scheme or 'http', 'all')


def partial_application(func):
    """
    Partially apply a function with arguments that are not provided.
    This is a helper to allow functions to be used as decorators or called directly.
    """
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


def extract_basic_auth(url):
    parts = urllib.parse.urlsplit(url)
    if parts.username is None:
        return url, None
    url = urllib.parse.urlunsplit(parts._replace(netloc=(
        parts.hostname if parts.port is None
        else f'{parts.hostname}:{parts.port}')))
    auth_payload = base64.b64encode(
        ('{}:{}'.format(parts.username, parts.password or '')).encode())
    return url, f'Basic {auth_payload.decode()}'


def smuggle_url(url, data):
    """ Pass additional data in a URL for internal use. """

    url, idata = unsmuggle_url(url, {})
    data.update(idata)
    sdata = urllib.parse.urlencode(
        {'__youtubedl_smuggle': json.dumps(data)})
    return url + '#' + sdata


def unsmuggle_url(smug_url, default=None):
    if '#__youtubedl_smuggle' not in smug_url:
        return smug_url, default
    url, _, sdata = smug_url.rpartition('#')
    jsond = urllib.parse.parse_qs(sdata)['__youtubedl_smuggle'][0]
    data = json.loads(jsond)
    return url, data


def get_domain(url):
    """
    This implementation is inconsistent, but is kept for compatibility.
    Use this only for "webpage_url_domain"
    """
    return remove_start(urllib.parse.urlparse(url).netloc, 'www.') or None


def url_basename(url):
    path = urllib.parse.urlparse(url).path
    return path.strip('/').split('/')[-1]


def base_url(url):
    return re.match(r'https?://[^?#]+/', url).group()


@partial_application
def urljoin(base, path):
    if isinstance(path, bytes):
        path = path.decode()
    if not isinstance(path, str) or not path:
        return None
    if re.match(r'(?:[a-zA-Z][a-zA-Z0-9+-.]*:)?//', path):
        return path
    if isinstance(base, bytes):
        base = base.decode()
    if not isinstance(base, str) or not re.match(
            r'^(?:https?:)?//', base):
        return None
    return urllib.parse.urljoin(base, path)


def urlencode_postdata(*args, **kargs):
    return urllib.parse.urlencode(*args, **kargs).encode('ascii')


@partial_application
def update_url(url, *, query_update=None, **kwargs):
    """Replace URL components specified by kwargs
       @param url           str or parse url tuple
       @param query_update  update query
       @returns             str
    """
    if isinstance(url, str):
        if not kwargs and not query_update:
            return url
        else:
            url = urllib.parse.urlparse(url)
    if query_update:
        assert 'query' not in kwargs, 'query_update and query cannot be specified at the same time'
        kwargs['query'] = urllib.parse.urlencode({
            **urllib.parse.parse_qs(url.query),
            **query_update,
        }, True)
    return urllib.parse.urlunparse(url._replace(**kwargs))


@partial_application
def update_url_query(url, query):
    return update_url(url, query_update=query)


def _multipart_encode_impl(data, boundary):
    content_type = f'multipart/form-data; boundary={boundary}'

    out = b''
    for k, v in data.items():
        out += b'--' + boundary.encode('ascii') + b'\r\n'
        if isinstance(k, str):
            k = k.encode()
        if isinstance(v, str):
            v = v.encode()
        # RFC 2047 requires non-ASCII field names to be encoded, while RFC 7578
        # suggests sending UTF-8 directly. Firefox sends UTF-8, too
        content = b'Content-Disposition: form-data; name="' + k + b'"\r\n\r\n' + v + b'\r\n'
        if boundary.encode('ascii') in content:
            raise ValueError('Boundary overlaps with data')
        out += content

    out += b'--' + boundary.encode('ascii') + b'--\r\n'

    return out, content_type


def multipart_encode(data, boundary=None):
    """
    Encode a dict to RFC 7578-compliant form-data

    data:
        A dict where keys and values can be either Unicode or bytes-like
        objects.
    boundary:
        If specified a Unicode object, it's used as the boundary. Otherwise
        a random boundary is generated.

    Reference: https://tools.ietf.org/html/rfc7578
    """
    has_specified_boundary = boundary is not None

    while True:
        if boundary is None:
            boundary = '---------------' + str(random.randrange(0x0fffffff, 0xffffffff))

        try:
            out, content_type = _multipart_encode_impl(data, boundary)
            break
        except ValueError:
            if has_specified_boundary:
                raise
            boundary = None

    return out, content_type
