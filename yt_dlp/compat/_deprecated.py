"""Deprecated - New code should avoid these.

The actual implementation has been moved to yt_dlp.deprecated.compat_deprecated.
This file is kept as a re-export shim for backward compatibility.
"""
from .compat_utils import passthrough_module

passthrough_module(__name__, 'yt_dlp.deprecated.compat_deprecated')
del passthrough_module
