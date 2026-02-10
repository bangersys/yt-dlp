import collections.abc


def variadic(x, allowed_types=(str, bytes)):
    if x is None:
        return
    if isinstance(x, collections.abc.Iterable) and not isinstance(x, allowed_types):
        yield from x
    else:
        yield x


__all__ = [
    'variadic',
]
