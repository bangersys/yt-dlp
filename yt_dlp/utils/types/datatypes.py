import collections.abc
import functools
import inspect
import itertools
import time
import types
import typing


class LazyList(collections.abc.Sequence):
    """Lazy immutable list from an iterable
    Note that slices of a LazyList are lists and not LazyList"""

    class IndexError(IndexError):  # noqa: A001
        pass

    def __init__(self, iterable, *, reverse=False, _cache=None):
        self._iterable = iter(iterable)
        self._cache = [] if _cache is None else _cache
        self._reversed = reverse

    def __iter__(self):
        if self._reversed:
            # We need to consume the entire iterable to iterate in reverse
            yield from self.exhaust()
            return
        yield from self._cache
        for item in self._iterable:
            self._cache.append(item)
            yield item

    def _exhaust(self):
        self._cache.extend(self._iterable)
        self._iterable = []  # Discard the emptied iterable to make it pickle-able
        return self._cache

    def exhaust(self):
        """Evaluate the entire iterable"""
        return self._exhaust()[::-1 if self._reversed else 1]

    @staticmethod
    def _reverse_index(x):
        return None if x is None else ~x

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            if self._reversed:
                idx = slice(self._reverse_index(idx.start), self._reverse_index(idx.stop), -(idx.step or 1))
            start, stop, step = idx.start, idx.stop, idx.step or 1
        elif isinstance(idx, int):
            if self._reversed:
                idx = self._reverse_index(idx)
            start, stop, step = idx, idx, 0
        else:
            raise TypeError('indices must be integers or slices')
        if ((start or 0) < 0 or (stop or 0) < 0
                or (start is None and step < 0)
                or (stop is None and step > 0)):
            # We need to consume the entire iterable to be able to slice from the end
            # Obviously, never use this with infinite iterables
            self._exhaust()
            try:
                return self._cache[idx]
            except IndexError as e:
                raise self.IndexError(e) from e
        n = max(start or 0, stop or 0) - len(self._cache) + 1
        if n > 0:
            self._cache.extend(itertools.islice(self._iterable, n))
        try:
            return self._cache[idx]
        except IndexError as e:
            raise self.IndexError(e) from e

    def __bool__(self):
        try:
            self[-1] if self._reversed else self[0]
        except self.IndexError:
            return False
        return True

    def __len__(self):
        self._exhaust()
        return len(self._cache)

    def __reversed__(self):
        return type(self)(self._iterable, reverse=not self._reversed, _cache=self._cache)

    def __copy__(self):
        return type(self)(self._iterable, reverse=self._reversed, _cache=self._cache)

    def __repr__(self):
        # repr and str should mimic a list. So we exhaust the iterable
        return repr(self.exhaust())

    def __str__(self):
        return repr(self.exhaust())


class PagedList:

    class IndexError(IndexError):  # noqa: A001
        pass

    def __len__(self):
        # This is only useful for tests
        return len(self.getslice())

    def __init__(self, pagefunc, pagesize, use_cache=True):
        self._pagefunc = pagefunc
        self._pagesize = pagesize
        self._pagecount = float('inf')
        self._use_cache = use_cache
        self._cache = {}

    def getpage(self, pagenum):
        page_results = self._cache.get(pagenum)
        if page_results is None:
            page_results = [] if pagenum > self._pagecount else list(self._pagefunc(pagenum))
        if self._use_cache:
            self._cache[pagenum] = page_results
        return page_results

    def getslice(self, start=0, end=None):
        return list(self._getslice(start, end))

    def _getslice(self, start, end):
        raise NotImplementedError('This method must be implemented by subclasses')

    def __getitem__(self, idx):
        assert self._use_cache, 'Indexing PagedList requires cache'
        if not isinstance(idx, int) or idx < 0:
            raise TypeError('indices must be non-negative integers')
        entries = self.getslice(idx, idx + 1)
        if not entries:
            raise self.IndexError
        return entries[0]

    def __bool__(self):
        return bool(self.getslice(0, 1))


class OnDemandPagedList(PagedList):
    """Download pages until a page with less than maximum results"""

    def _getslice(self, start, end):
        for pagenum in itertools.count(start // self._pagesize):
            firstid = pagenum * self._pagesize
            nextfirstid = pagenum * self._pagesize + self._pagesize
            if start >= nextfirstid:
                continue

            startv = (
                start % self._pagesize
                if firstid <= start < nextfirstid
                else 0)
            endv = (
                ((end - 1) % self._pagesize) + 1
                if (end is not None and firstid <= end <= nextfirstid)
                else None)

            try:
                page_results = self.getpage(pagenum)
            except Exception:
                self._pagecount = pagenum - 1
                raise
            if startv != 0 or endv is not None:
                page_results = page_results[startv:endv]
            yield from page_results

            # A little optimization - if current page is not "full", ie. does
            # not contain page_size videos then we can assume that this page
            # is the last one - there are no more ids on further pages -
            # i.e. no need to query again.
            if len(page_results) + startv < self._pagesize:
                break

            # If we got the whole page, but the next page is not interesting,
            # break out early as well
            if end == nextfirstid:
                break


class InAdvancePagedList(PagedList):
    """PagedList with total number of pages known in advance"""

    def __init__(self, pagefunc, pagecount, pagesize):
        PagedList.__init__(self, pagefunc, pagesize, True)
        self._pagecount = pagecount

    def _getslice(self, start, end):
        start_page = start // self._pagesize
        end_page = self._pagecount if end is None else min(self._pagecount, end // self._pagesize + 1)
        skip_elems = start - start_page * self._pagesize
        only_more = None if end is None else end - start
        for pagenum in range(start_page, end_page):
            page_results = self.getpage(pagenum)
            if skip_elems:
                page_results = page_results[skip_elems:]
                skip_elems = 0
            if only_more is not None:
                if len(page_results) < only_more:
                    only_more -= len(page_results)
                else:
                    yield from page_results[:only_more]
                    break
            yield from page_results


def cached_method(f):
    """Cache a method"""
    signature = inspect.signature(f)

    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        bound_args = signature.bind(self, *args, **kwargs)
        bound_args.apply_defaults()
        key = tuple(bound_args.arguments.values())[1:]

        cache = vars(self).setdefault('_cached_method__cache', {}).setdefault(f.__name__, {})
        if key not in cache:
            cache[key] = f(self, *args, **kwargs)
        return cache[key]
    return wrapper


class classproperty:
    """property access for class methods with optional caching"""
    def __new__(cls, func=None, *args, **kwargs):
        if not func:
            return functools.partial(cls, *args, **kwargs)
        return super().__new__(cls)

    def __init__(self, func, *, cache=False):
        functools.update_wrapper(self, func)
        self.func = func
        self._cache = {} if cache else None

    def __get__(self, _, cls):
        if self._cache is None:
            return self.func(cls)
        elif cls not in self._cache:
            self._cache[cls] = self.func(cls)
        return self._cache[cls]


class function_with_repr:
    def __init__(self, func, repr_=None):
        functools.update_wrapper(self, func)
        self.func, self.__repr = func, repr_

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    @classmethod
    def set_repr(cls, repr_):
        return functools.partial(cls, repr_=repr_)

    def __repr__(self):
        if self.__repr:
            return self.__repr
        return f'{self.func.__module__}.{self.func.__qualname__}'


from ...constants import Namespace


class RetryManager:
    """Usage:
        for retry in RetryManager(...):
            try:
                ...
            except SomeException as err:
                retry.error = err
                continue
    """
    attempt, _error = 0, None

    def __init__(self, _retries, _error_callback, **kwargs):
        self.retries = _retries or 0
        self.error_callback = functools.partial(_error_callback, **kwargs)

    def _should_retry(self):
        from ...constants import NO_DEFAULT
        return self._error is not NO_DEFAULT and self.attempt <= self.retries

    @property
    def error(self):
        from ...constants import NO_DEFAULT
        if self._error is NO_DEFAULT:
            return None
        return self._error

    @error.setter
    def error(self, value):
        self._error = value

    def __iter__(self):
        from ...constants import NO_DEFAULT
        while self._should_retry():
            self.error = NO_DEFAULT
            self.attempt += 1
            yield self
            if self.error:
                self.error_callback(self.error, self.attempt, self.retries)

    @staticmethod
    def report_retry(e, count, retries, *, sleep_func, info, warn, error=None, suffix=None):
        """Utility function for reporting retries"""
        from .exceptions import ExtractorError
        from ..formatting import format_field, remove_end, str_or_none, float_or_none

        if count > retries:
            if error:
                return error(f'{e}. Giving up after {count - 1} retries') if count > 1 else error(str(e))
            raise e

        if not count:
            return warn(e)
        elif isinstance(e, ExtractorError):
            e = remove_end(str_or_none(e.cause) or e.orig_msg, '.')
        warn(f'{e}. Retrying{format_field(suffix, None, " %s")} ({count}/{retries})...')

        delay = float_or_none(sleep_func(n=count - 1)) if callable(sleep_func) else sleep_func
        if delay:
            info(f'Sleeping {delay:.2f} seconds ...')
            time.sleep(delay)




class ISO639Utils:
    # See http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt
    _lang_map = {
        'aa': 'aar',
        'ab': 'abk',
        'ae': 'ave',
        'af': 'afr',
        'ak': 'aka',
        'am': 'amh',
        'an': 'arg',
        'ar': 'ara',
        'as': 'asm',
        'av': 'ava',
        'ay': 'aym',
        'az': 'aze',
        'ba': 'bak',
        'be': 'bel',
        'bg': 'bul',
        'bh': 'bih',
        'bi': 'bis',
        'bm': 'bam',
        'bn': 'ben',
        'bo': 'bod',
        'br': 'bre',
        'bs': 'bos',
        'ca': 'cat',
        'ce': 'che',
        'ch': 'cha',
        'co': 'cos',
        'cr': 'cre',
        'cs': 'ces',
        'cu': 'chu',
        'cv': 'chv',
        'cy': 'cym',
        'da': 'dan',
        'de': 'deu',
        'dv': 'div',
        'dz': 'dzo',
        'ee': 'ewe',
        'el': 'ell',
        'en': 'eng',
        'eo': 'epo',
        'es': 'spa',
        'et': 'est',
        'eu': 'eus',
        'fa': 'fas',
        'ff': 'ful',
        'fi': 'fin',
        'fj': 'fij',
        'fo': 'fao',
        'fr': 'fra',
        'fy': 'fry',
        'ga': 'gle',
        'gd': 'gla',
        'gl': 'glg',
        'gn': 'grn',
        'gu': 'guj',
        'gv': 'glv',
        'ha': 'hau',
        'he': 'heb',
        'iw': 'heb',  # Replaced by he in 1989 revision
        'hi': 'hin',
        'ho': 'hmo',
        'hr': 'hrv',
        'ht': 'hat',
        'hu': 'hun',
        'hy': 'hye',
        'hz': 'her',
        'ia': 'ina',
        'id': 'ind',
        'in': 'ind',  # Replaced by id in 1989 revision
        'ie': 'ile',
        'ig': 'ibo',
        'ii': 'iii',
        'ik': 'ipk',
        'io': 'ido',
        'is': 'isl',
        'it': 'ita',
        'iu': 'iku',
        'ja': 'jpn',
        'jv': 'jav',
        'ka': 'kat',
        'kg': 'kon',
        'ki': 'kik',
        'kj': 'kua',
        'kk': 'kaz',
        'kl': 'kal',
        'km': 'khm',
        'kn': 'kan',
        'ko': 'kor',
        'kr': 'kau',
        'ks': 'kas',
        'ku': 'kur',
        'kv': 'kom',
        'kw': 'cor',
        'ky': 'kir',
        'la': 'lat',
        'lb': 'ltz',
        'lg': 'lug',
        'li': 'lim',
        'ln': 'lin',
        'lo': 'lao',
        'lt': 'lit',
        'lu': 'lub',
        'lv': 'lav',
        'mg': 'mlg',
        'mh': 'mah',
        'mi': 'mri',
        'mk': 'mkd',
        'ml': 'mal',
        'mn': 'mon',
        'mr': 'mar',
        'ms': 'msa',
        'mt': 'mlt',
        'my': 'mya',
        'na': 'nau',
        'nb': 'nob',
        'nd': 'nde',
        'ne': 'nep',
        'ng': 'ndo',
        'nl': 'nld',
        'nn': 'nno',
        'no': 'nor',
        'nr': 'nbl',
        'nv': 'nav',
        'ny': 'nya',
        'oc': 'oci',
        'oj': 'oji',
        'om': 'orm',
        'or': 'ori',
        'os': 'oss',
        'pa': 'pan',
        'pe': 'per',
        'pi': 'pli',
        'pl': 'pol',
        'ps': 'pus',
        'pt': 'por',
        'qu': 'que',
        'rm': 'roh',
        'rn': 'run',
        'ro': 'ron',
        'ru': 'rus',
        'rw': 'kin',
        'sa': 'san',
        'sc': 'srd',
        'sd': 'snd',
        'se': 'sme',
        'sg': 'sag',
        'si': 'sin',
        'sk': 'slk',
        'sl': 'slv',
        'sm': 'smo',
        'sn': 'sna',
        'so': 'som',
        'sq': 'sqi',
        'sr': 'srp',
        'ss': 'ssw',
        'st': 'sot',
        'su': 'sun',
        'sv': 'swe',
        'sw': 'swa',
        'ta': 'tam',
        'te': 'tel',
        'tg': 'tgk',
        'th': 'tha',
        'ti': 'tir',
        'tk': 'tuk',
        'tl': 'tgl',
        'tn': 'tsn',
        'to': 'ton',
        'tr': 'tur',
        'ts': 'tso',
        'tt': 'tat',
        'tw': 'twi',
        'ty': 'tah',
        'ug': 'uig',
        'uk': 'ukr',
        'ur': 'urd',
        'uz': 'uzb',
        've': 'ven',
        'vi': 'vie',
        'vo': 'vol',
        'wa': 'wln',
        'wo': 'wol',
        'xh': 'xho',
        'yi': 'yid',
        'ji': 'yid',  # Replaced by yi in 1989 revision
        'yo': 'yor',
        'za': 'zha',
        'zh': 'zho',
        'zu': 'zul',
    }

    @classmethod
    def short2long(cls, code):
        """Convert language code from ISO 639-1 to ISO 639-2/T"""
        return cls._lang_map.get(code[:2])

    @classmethod
    def long2short(cls, code):
        """Convert language code from ISO 639-2/T to ISO 639-1"""
        for short_name, long_name in cls._lang_map.items():
            if long_name == code:
                return short_name
