from __future__ import annotations

import collections
import collections.abc
import contextlib
import functools
import http.cookies
import html.entities
import html.parser
import inspect
import itertools
import re
import typing
import xml.etree.ElementTree

from ..compat import compat_HTMLParseError
from ._utils import (
    IDENTITY,
    NO_DEFAULT,
    ExtractorError,
    deprecation_warning,
    is_iterable_like,
    try_call,
    url_or_none,
    variadic,
)
from .types import LazyList


class HTMLBreakOnClosingTagParser(html.parser.HTMLParser):
    """
    HTML parser which raises HTMLBreakOnClosingTagException upon reaching the
    closing tag for the first opening tag it has encountered.
    """

    class HTMLBreakOnClosingTagException(Exception):
        pass

    def __init__(self):
        self.tagstack = collections.deque()
        super().__init__()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        # handle_endtag does not return upon raising HTMLBreakOnClosingTagException,
        # so data remains buffered; we no longer have any interest in it, thus
        # override this method to discard it
        pass

    def handle_starttag(self, tag, _):
        self.tagstack.append(tag)

    def handle_endtag(self, tag):
        if not self.tagstack:
            raise compat_HTMLParseError('no tags in the stack')
        while self.tagstack:
            inner_tag = self.tagstack.pop()
            if inner_tag == tag:
                break
        else:
            raise compat_HTMLParseError(f'matching opening tag for closing {tag} tag not found')
        if not self.tagstack:
            raise self.HTMLBreakOnClosingTagException


class HTMLAttributeParser(html.parser.HTMLParser):
    """Trivial HTML parser to gather the attributes for a single element"""

    def __init__(self):
        self.attrs = {}
        super().__init__()

    def handle_starttag(self, tag, attrs):
        self.attrs = dict(attrs)
        raise compat_HTMLParseError('done')


class HTMLListAttrsParser(html.parser.HTMLParser):
    """HTML parser to gather the attributes for the elements of a list"""

    def __init__(self):
        super().__init__()
        self.items = []
        self._level = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'li' and self._level == 0:
            self.items.append(dict(attrs))
        self._level += 1

    def handle_endtag(self, tag):
        self._level -= 1


def _htmlentity_transform(entity_with_semicolon):
    """Transforms an HTML entity to a character."""
    entity = entity_with_semicolon[:-1]
    if entity in html.entities.name2codepoint:
        return chr(html.entities.name2codepoint[entity])
    if entity_with_semicolon in html.entities.html5:
        return html.entities.html5[entity_with_semicolon]

    mobj = re.match(r'#(x[0-9a-fA-F]+|[0-9]+)', entity)
    if mobj is not None:
        numstr = mobj.group(1)
        base = 16 if numstr.startswith('x') else 10
        if base == 16:
            numstr = f'0{numstr}'
        with contextlib.suppress(ValueError):
            return chr(int(numstr, base))
    return f'&{entity};'


def unescapeHTML(s):
    """
    Research Note: Core utility for cleaning extracted HTML content.
    Essential for parsing metadata that has been entity-encoded for web display.
    """
    if s is None:
        return None
    assert isinstance(s, str)
    return re.sub(r'&([^&;]+;)', lambda m: _htmlentity_transform(m.group(1)), s)


def clean_html(html):
    """
    Clean an HTML snippet into a readable string.
    Research Note: This is a robust cleaner that handles br tags, paragraphs,
    and strips all other HTML tags while unescaping entities.
    """
    if html is None:  # Convenience for sanitizing descriptions etc.
        return html

    html = re.sub(r'\s+', ' ', html)
    html = re.sub(r'(?u)\s?<\s?br\s?/?\s?>\s?', '\n', html)
    html = re.sub(r'(?u)<\s?/\s?p\s?>\s?<\s?p[^>]*>', '\n', html)
    # Strip html tags
    html = re.sub('<.*?>', '', html)
    # Replace html entities
    html = unescapeHTML(html)
    return html.strip()


def escapeHTML(text):
    """HTML-escape a string."""
    return (
        text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )


def get_element_text_and_html_by_tag(tag, html):
    """
    For the first element with the specified tag in the passed HTML document
    return its content (text) and the whole element (html).
    """
    def find_or_raise(haystack, needle, exc):
        try:
            return haystack.index(needle)
        except ValueError:
            raise exc

    closing_tag = f'</{tag}>'
    whole_start = find_or_raise(html, f'<{tag}', compat_HTMLParseError(f'opening {tag} tag not found'))
    content_start = find_or_raise(html[whole_start:], '>', compat_HTMLParseError(f'malformed opening {tag} tag'))
    content_start += whole_start + 1
    with HTMLBreakOnClosingTagParser() as parser:
        parser.feed(html[whole_start:content_start])
        if not parser.tagstack or parser.tagstack[0] != tag:
            raise compat_HTMLParseError(f'parser did not match opening {tag} tag')
        offset = content_start
        while offset < len(html):
            next_closing_tag_start = find_or_raise(
                html[offset:], closing_tag, compat_HTMLParseError(f'closing {tag} tag not found'))
            next_closing_tag_end = next_closing_tag_start + len(closing_tag)
            try:
                parser.feed(html[offset:offset + next_closing_tag_end])
                offset += next_closing_tag_end
            except HTMLBreakOnClosingTagParser.HTMLBreakOnClosingTagException:
                return html[content_start:offset + next_closing_tag_start], \
                    html[whole_start:offset + next_closing_tag_end]
        raise compat_HTMLParseError('unexpected end of html')


def get_elements_text_and_html_by_attribute(attribute, value, html, *, tag=r'[\w:.-]+', escape_value=True):
    """
    Return the text (content) and the html (whole) of the tag with the specified
    attribute in the passed HTML document.
    """
    if not value:
        return
    quote = '' if re.match(r'''[\s"'`=<>]''', value) else '?'
    value = re.escape(value) if escape_value else value
    partial_element_re = rf'''(?x)
        <(?P<tag>{tag})
         (?:\s(?:[^>"']|"[^"]*"|'[^']*')*)?
         \s{re.escape(attribute)}\s*=\s*(?P<_q>['"]{quote})(?-x:{value})(?P=_q)
        '''
    for m in re.finditer(partial_element_re, html):
        content, whole = get_element_text_and_html_by_tag(m.group('tag'), html[m.start():])
        yield (
            unescapeHTML(re.sub(r'^(?P<q>["\'])(?P<content>.*)(?P=q)$', r'\g<content>', content, flags=re.DOTALL)),
            whole,
        )


def get_element_by_id(id, html, **kwargs):
    return get_element_by_attribute('id', id, html, **kwargs)


def get_element_html_by_id(id, html, **kwargs):
    return get_element_html_by_attribute('id', id, html, **kwargs)


def get_element_by_class(class_name, html):
    retval = get_elements_by_class(class_name, html)
    return retval[0] if retval else None


def get_element_html_by_class(class_name, html):
    retval = get_elements_html_by_class(class_name, html)
    return retval[0] if retval else None


def get_element_by_attribute(attribute, value, html, **kwargs):
    retval = get_elements_by_attribute(attribute, value, html, **kwargs)
    return retval[0] if retval else None


def get_element_html_by_attribute(attribute, value, html, **kargs):
    retval = get_elements_html_by_attribute(attribute, value, html, **kargs)
    return retval[0] if retval else None


def get_elements_by_class(class_name, html, **kargs):
    return get_elements_by_attribute(
        'class', rf'[^\'"]*(?<=[\'"\s]){re.escape(class_name)}(?=[\'"\s])[^\'"]*',
        html, escape_value=False)


def get_elements_html_by_class(class_name, html):
    return get_elements_html_by_attribute(
        'class', rf'[^\'"]*(?<=[\'"\s]){re.escape(class_name)}(?=[\'"\s])[^\'"]*',
        html, escape_value=False)


def get_elements_by_attribute(*args, **kwargs):
    return [content for content, _ in get_elements_text_and_html_by_attribute(*args, **kwargs)]


def get_elements_html_by_attribute(*args, **kwargs):
    return [whole for _, whole in get_elements_text_and_html_by_attribute(*args, **kwargs)]


def extract_attributes(html_element):
    """
    Given a string for an HTML element, decode and return a dictionary of attributes.
    """
    parser = HTMLAttributeParser()
    with contextlib.suppress(compat_HTMLParseError):
        parser.feed(html_element)
        parser.close()
    return parser.attrs


def parse_list(webpage):
    """
    Given a string for an series of HTML <li> elements, return a dictionary of their attributes.
    """
    parser = HTMLListAttrsParser()
    parser.feed(webpage)
    parser.close()
    return parser.items


def traverse_obj(
        obj, *paths, default=NO_DEFAULT, expected_type=None, get_all=True,
        casesense=True, is_user_input=NO_DEFAULT, traverse_string=False):
    """
    Safely traverse nested `dict`s and `Iterable`s.
    Research Note: This is the high-level facade for data extraction in yt-dlp.
    It combines sequential path traversal with powerful branching, filtering,
    and transformation capabilities, tailored for noisy web data.
    """
    if is_user_input is not NO_DEFAULT:
        deprecation_warning('The is_user_input parameter is deprecated and no longer works')

    casefold = lambda k: k.casefold() if isinstance(k, str) else k

    if isinstance(expected_type, type):
        type_test = lambda val: val if isinstance(val, expected_type) else None
    else:
        type_test = lambda val: try_call(expected_type or IDENTITY, args=(val,))

    def apply_key(key, obj, is_last):
        branching = False
        result = None

        if obj is None and traverse_string:
            if key is ... or callable(key) or isinstance(key, slice):
                branching = True
                result = ()
        elif key is None:
            result = obj
        elif isinstance(key, set):
            item = next(iter(key))
            if len(key) > 1 or isinstance(item, type):
                assert all(isinstance(item, type) for item in key)
                if isinstance(obj, tuple(key)):
                    result = obj
            else:
                result = try_call(item, args=(obj,))
        elif isinstance(key, (list, tuple)):
            branching = True
            result = itertools.chain.from_iterable(
                apply_path(obj, branch, is_last)[0] for branch in key)
        elif key is ...:
            branching = True
            if isinstance(obj, http.cookies.Morsel):
                obj = dict(obj, key=obj.key, value=obj.value)
            if isinstance(obj, collections.abc.Mapping):
                result = obj.values()
            elif is_iterable_like(obj) or isinstance(obj, xml.etree.ElementTree.Element):
                result = obj
            elif isinstance(obj, re.Match):
                result = obj.groups()
            elif traverse_string:
                branching = False
                result = str(obj)
            else:
                result = ()
        elif callable(key):
            branching = True
            if isinstance(obj, http.cookies.Morsel):
                obj = dict(obj, key=obj.key, value=obj.value)
            if isinstance(obj, collections.abc.Mapping):
                iter_obj = obj.items()
            elif is_iterable_like(obj) or isinstance(obj, xml.etree.ElementTree.Element):
                iter_obj = enumerate(obj)
            elif isinstance(obj, re.Match):
                iter_obj = itertools.chain(
                    enumerate((obj.group(), *obj.groups())),
                    obj.groupdict().items())
            elif traverse_string:
                branching = False
                iter_obj = enumerate(str(obj))
            else:
                iter_obj = ()
            result = (v for k, v in iter_obj if try_call(key, args=(k, v)))
            if not branching:
                result = ''.join(result)
        elif isinstance(key, dict):
            iter_obj = ((k, _traverse_obj(obj, v, False, is_last)) for k, v in key.items())
            result = {
                k: v if v is not None else default for k, v in iter_obj
                if v is not None or default is not NO_DEFAULT
            } or None
        elif isinstance(obj, collections.abc.Mapping):
            if isinstance(obj, http.cookies.Morsel):
                obj = dict(obj, key=obj.key, value=obj.value)
            result = (try_call(obj.get, args=(key,)) if casesense or try_call(obj.__contains__, args=(key,)) else
                      next((v for k, v in obj.items() if casefold(k) == key), None))
        elif isinstance(obj, re.Match):
            if isinstance(key, int) or casesense:
                with contextlib.suppress(IndexError):
                    result = obj.group(key)
            elif isinstance(key, str):
                result = next((v for k, v in obj.groupdict().items() if casefold(k) == key), None)
        elif isinstance(key, (int, slice)):
            if is_iterable_like(obj, (collections.abc.Sequence, xml.etree.ElementTree.Element)):
                branching = isinstance(key, slice)
                with contextlib.suppress(IndexError):
                    result = obj[key]
            elif traverse_string:
                with contextlib.suppress(IndexError):
                    result = str(obj)[key]
        elif isinstance(obj, xml.etree.ElementTree.Element) and isinstance(key, str):
            xpath, _, special = key.rpartition('/')
            if not special.startswith('@') and not special.endswith('()'):
                xpath = key
                special = None
            if xpath.startswith('/'):
                xpath = f'.{xpath}'
            elif xpath and not xpath.startswith('./'):
                xpath = f'./{xpath}'

            def apply_specials(element):
                if special is None:
                    return element
                if special == '@':
                    return element.attrib
                if special.startswith('@'):
                    return try_call(element.attrib.get, args=(special[1:],))
                if special == 'text()':
                    return element.text
                raise SyntaxError(f'apply_specials is missing case for {special!r}')

            if xpath:
                result = list(map(apply_specials, obj.iterfind(xpath)))
            else:
                result = apply_specials(obj)

        return branching, result if branching else (result,)

    def lazy_last(iterable):
        iterator = iter(iterable)
        prev = next(iterator, NO_DEFAULT)
        if prev is NO_DEFAULT:
            return
        for item in iterator:
            yield False, prev
            prev = item
        yield True, prev

    def apply_path(start_obj, path, test_type):
        objs = (start_obj,)
        has_branched = False
        key = None
        for last, key in lazy_last(variadic(path, (str, bytes, dict, set))):
            if not casesense and isinstance(key, str):
                key = key.casefold()
            if key in (any, all):
                has_branched = False
                filtered_objs = (obj for obj in objs if obj not in (None, {}))
                objs = (next(filtered_objs, None),) if key is any else (list(filtered_objs),)
                continue
            if key is filter:
                objs = filter(None, objs)
                continue
            if __debug__ and callable(key):
                inspect.signature(key).bind(None, None)
            new_objs = []
            for obj in objs:
                branching, results = apply_key(key, obj, last)
                has_branched |= branching
                new_objs.append(results)
            objs = itertools.chain.from_iterable(new_objs)
        if test_type and not isinstance(key, (dict, list, tuple)):
            objs = map(type_test, objs)
        return objs, has_branched, isinstance(key, dict)

    def _traverse_obj(obj, path, allow_empty, test_type):
        results, has_branched, is_dict = apply_path(obj, path, test_type)
        results = LazyList(item for item in results if item not in (None, {}))
        if get_all and has_branched:
            if results:
                return results.exhaust()
            if allow_empty:
                return [] if default is NO_DEFAULT else default
            return None
        return results[0] if results else {} if allow_empty and is_dict else None

    for index, path in enumerate(paths, 1):
        is_last = index == len(paths)
        try:
            result = _traverse_obj(obj, path, is_last, True)
            if result is not None:
                return result
        except _RequiredError as e:
            if is_last:
                raise ExtractorError(e.orig_msg, expected=e.expected) from None
    return None if default is NO_DEFAULT else default


def value(value, /):
    return lambda _: value


def require(name, /, *, expected=False):
    def func(value):
        if value is None:
            raise _RequiredError(f'Unable to extract {name}', expected=expected)
        return value
    return func


class _RequiredError(ExtractorError):
    pass


def subs_list_to_dict(subs: list[dict] | None = None, /, *, lang='und', ext=None):
    if subs is None:
        return functools.partial(subs_list_to_dict, lang=lang, ext=ext)
    result = collections.defaultdict(list)
    for sub in subs:
        if not url_or_none(sub.get('url')) and not sub.get('data'):
            continue
        sub_id = sub.pop('id', None)
        if not isinstance(sub_id, str):
            sub_id = lang
        if not sub_id:
            continue
        sub_ext = sub.get('ext')
        if not isinstance(sub_ext, str):
            if not ext:
                sub.pop('ext', None)
            else:
                sub['ext'] = ext
        result[sub_id].append(sub)
    result = dict(result)
    for subs in result.values():
        subs.sort(key=lambda x: x.pop('quality', 0) or 0)
    return result


def find_element(*, tag=None, id=None, cls=None, attr=None, value=None, html=False, regex=False):
    assert tag or id or cls or (attr and value), 'One of tag, id, cls or (attr AND value) is required'
    ANY_TAG = r'[\w:.-]+'
    if attr and value:
        assert not cls, 'Cannot match both attr and cls'
        assert not id, 'Cannot match both attr and id'
        func = get_element_html_by_attribute if html else get_element_by_attribute
        return functools.partial(func, attr, value, tag=tag or ANY_TAG, escape_value=not regex)
    elif cls:
        assert not id, 'Cannot match both cls and id'
        assert tag is None, 'Cannot match both cls and tag'
        assert not regex, 'Cannot use regex with cls'
        func = get_element_html_by_class if html else get_element_by_class
        return functools.partial(func, cls)
    elif id:
        func = get_element_html_by_id if html else get_element_by_id
        return functools.partial(func, id, tag=tag or ANY_TAG, escape_value=not regex)
    index = int(bool(html))
    return lambda html: get_element_text_and_html_by_tag(tag, html)[index]


def find_elements(*, tag=None, cls=None, attr=None, value=None, html=False, regex=False):
    assert cls or (attr and value), 'One of cls or (attr AND value) is required'
    if attr and value:
        assert not cls, 'Cannot match both attr and cls'
        func = get_elements_html_by_attribute if html else get_elements_by_attribute
        return functools.partial(func, attr, value, tag=tag or r'[\w:.-]+', escape_value=not regex)
    assert not tag, 'Cannot match both cls and tag'
    assert not regex, 'Cannot use regex with cls'
    func = get_elements_html_by_class if html else get_elements_by_class
    return functools.partial(func, cls)


def trim_str(*, start=None, end=None):
    def trim(s):
        if s is None:
            return None
        start_idx = len(start) if start and s.startswith(start) else 0
        if end and s.endswith(end):
            return s[start_idx:-len(end)]
        return s[start_idx:]
    return trim


def unpack(func, **kwargs):
    @functools.wraps(func)
    def inner(items):
        return func(*items, **kwargs)
    return inner


def get_first(obj, *paths, **kwargs):
    return traverse_obj(obj, *((..., *variadic(keys)) for keys in paths), **kwargs, get_all=False)


def dict_get(d, key_or_keys, default=None, skip_false_values=True):
    for val in map(d.get, variadic(key_or_keys)):
        if val is not None and (val or not skip_false_values):
            return val
    return default
