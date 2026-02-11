# flake8: noqa: F403
from ..compat.compat_utils import passthrough_module

passthrough_module(__name__, '._deprecated')
del passthrough_module

# isort: off
from .traversal import *
from .filesystem import *
from .formatting import *
from .json import *
from .datetime import *
from .math import *
from .xml import *
from .subtitles import *
from .progress import *
from .version import *
from .crypto import *

from ._utils import *
from ._json import *
from .download import download_range_func
from . import crypto, types
from ._utils import _UnsafeExtensionError
from .types import *
from ..constants import IDENTITY, NO_DEFAULT  # noqa: F401

# Prefer traversal as source of truth for traversal/html helper utilities
from .traversal import (
    HTMLAttributeParser,
    HTMLBreakOnClosingTagParser,
    HTMLListAttrsParser,
    clean_html,
    escapeHTML,
    extract_attributes,
    get_element_by_attribute,
    get_element_by_class,
    get_element_by_id,
    get_element_html_by_attribute,
    get_element_html_by_class,
    get_element_html_by_id,
    get_element_text_and_html_by_tag,
    get_elements_by_attribute,
    get_elements_by_class,
    get_elements_html_by_attribute,
    get_elements_html_by_class,
    get_elements_text_and_html_by_attribute,
    unescapeHTML,
)

