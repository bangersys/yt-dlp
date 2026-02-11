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
from .math import lookup_unit_table, parse_filesize
from .types import *
from ._utils import *
from ._json import *
from ._utils import _configuration_args, _get_exe_version_output  # noqa: F401
from . import geo
from ..constants import IDENTITY, NO_DEFAULT, Namespace  # noqa: F401

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
    parse_list,
    unescapeHTML,
)
