"""
Centralized home for all deprecated and legacy API shims.

Everything here exists solely for backward compatibility with external code
and plugins. New code should NOT import from this package.

Submodules (import directly, e.g. ``from yt_dlp.deprecated.utils_legacy import X``):

- ``utils_legacy``      — Old networking shims, dead code, trivial wrappers
- ``utils_deprecated``  — bytes_to_intlist, jwt_encode_hs256, compiled_regex_type
- ``compat_legacy``     — ~60 compat_* stdlib aliases
- ``compat_deprecated`` — compat_os_name, compat_realpath, compat_shlex_quote
"""
