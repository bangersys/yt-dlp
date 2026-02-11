import sys

if sys.version_info < (3, 10):
    raise ImportError(
        f'You are using an unsupported version of Python. Only Python versions 3.10 and above are supported by yt-dlp')  # noqa: F541

__license__ = 'The Unlicense'

from .globals import IN_CLI, plugin_dirs
from .utils._utils import _UnsafeExtensionError


from .extractor import gen_extractors, list_extractors
from .YoutubeDL import YoutubeDL


def parse_options(argv=None):
    from .cli import parse_options
    return parse_options(argv)


def main(argv=None):
    from .cli import main
    return main(argv)

__all__ = [
    'YoutubeDL',
    'gen_extractors',
    'list_extractors',
    'main',
    'parse_options',
]
