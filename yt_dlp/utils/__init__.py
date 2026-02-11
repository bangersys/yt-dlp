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

from ._utils import *
from ._json import *
from ._utils import _configuration_args  # noqa: F401
from .download import download_range_func
from . import geo
from ..constants import IDENTITY, NO_DEFAULT  # noqa: F401

# Prefer traversal as source of truth for traversal/html helper utilities
from .datatypes import *
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
    parse_list,
    unescapeHTML,
)
