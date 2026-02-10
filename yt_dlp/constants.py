"""Project-wide constants.

This module centralizes immutable values that are shared across multiple
submodules to keep related definitions in one place and reduce duplication.
"""

SEARCH_EXAMPLES = (
    'cute kittens',
    'slithering pythons',
    'falling cat',
    'angry poodle',
    'purple fish',
    'running tortoise',
    'sleeping bunny',
    'burping cow',
)

# Browser/cookie constants
CHROMIUM_BASED_BROWSERS = {'brave', 'chrome', 'chromium', 'edge', 'opera', 'vivaldi', 'whale'}
SUPPORTED_BROWSERS = CHROMIUM_BASED_BROWSERS | {'firefox', 'safari'}

# Networking constants
USER_AGENT_TMPL = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Safari/537.36'
)
# Target versions released within the last ~6 months
CHROME_MAJOR_VERSION_RANGE = (137, 143)

# Updater constants
UPDATE_SOURCES = {
    'stable': 'yt-dlp/yt-dlp',
    'nightly': 'yt-dlp/yt-dlp-nightly-builds',
    'master': 'yt-dlp/yt-dlp-master-builds',
}
REPOSITORY = UPDATE_SOURCES['stable']
API_BASE_URL = 'https://api.github.com/repos'
API_URL = f'{API_BASE_URL}/{REPOSITORY}/releases'

FILE_SUFFIXES = {
    'zip': '',
    'win_exe': '.exe',
    'win_x86_exe': '_x86.exe',
    'win_arm64_exe': '_arm64.exe',
    'darwin_exe': '_macos',
    'linux_exe': '_linux',
    'linux_aarch64_exe': '_linux_aarch64',
    'musllinux_exe': '_musllinux',
    'musllinux_aarch64_exe': '_musllinux_aarch64',
}

NON_UPDATEABLE_REASONS = {
    **dict.fromkeys(FILE_SUFFIXES),  # Updatable
    **dict.fromkeys(
        ['linux_armv7l_dir', *(f'{variant[:-4]}_dir' for variant in FILE_SUFFIXES if variant.endswith('_exe'))],
        'Auto-update is not supported for unpackaged executables; Re-download the latest release'),
    'py2exe': 'py2exe is no longer supported by yt-dlp; This executable cannot be updated',
    'source': 'You cannot update when running from source code; Use git to pull the latest changes',
    'unknown': 'You installed yt-dlp from a manual build or with a package manager; Use that to update',
    'other': 'You are using an unofficial build of yt-dlp; Build the executable again',
}

# FFmpeg postprocessing constants
EXT_TO_OUT_FORMATS = {
    'aac': 'adts',
    'flac': 'flac',
    'm4a': 'ipod',
    'mka': 'matroska',
    'mkv': 'matroska',
    'mpg': 'mpeg',
    'ogv': 'ogg',
    'ts': 'mpegts',
    'wma': 'asf',
    'wmv': 'asf',
    'weba': 'webm',
    'vtt': 'webvtt',
}

ACODECS = {
    # name: (ext, encoder, opts)
    'mp3': ('mp3', 'libmp3lame', ()),
    'aac': ('m4a', 'aac', ('-f', 'adts')),
    'm4a': ('m4a', 'aac', ('-bsf:a', 'aac_adtstoasc')),
    'opus': ('opus', 'libopus', ()),
    'vorbis': ('ogg', 'libvorbis', ()),
    'flac': ('flac', 'flac', ()),
    'alac': ('m4a', None, ('-acodec', 'alac')),
    'wav': ('wav', None, ('-f', 'wav')),
}


# Shell quoting constants (Windows)
WINDOWS_QUOTE_TRANS = {
    '"': R'\"',
}
CMD_QUOTE_TRANS = {
    # Keep quotes balanced by replacing them with `""` instead of `\"`
    '"': '""',
    # These require an env-variable `=` containing `"^\n\n"`
    # `=` should be unique since variables containing `=` cannot be set using cmd
    '\n': '%=%',
    '\r': '%=%',
    # Use zero length variable replacement so `%` doesn't get expanded
    # `cd` is always set as long as extensions are enabled (`/E:ON` in `utils.Popen`)
    '%': '%%cd:~,%',
}

# Filesize parsing constants
FILE_SIZE_UNITS = {
    'B': 1,
    'b': 1,
    'bytes': 1,
    'KiB': 1024,
    'KB': 1000,
    'kB': 1024,
    'Kb': 1000,
    'kb': 1000,
    'kilobytes': 1000,
    'kibibytes': 1024,
    'MiB': 1024 ** 2,
    'MB': 1000 ** 2,
    'mB': 1024 ** 2,
    'Mb': 1000 ** 2,
    'mb': 1000 ** 2,
    'megabytes': 1000 ** 2,
    'mebibytes': 1024 ** 2,
    'GiB': 1024 ** 3,
    'GB': 1000 ** 3,
    'gB': 1024 ** 3,
    'Gb': 1000 ** 3,
    'gb': 1000 ** 3,
    'gigabytes': 1000 ** 3,
    'gibibytes': 1024 ** 3,
    'TiB': 1024 ** 4,
    'TB': 1000 ** 4,
    'tB': 1024 ** 4,
    'Tb': 1000 ** 4,
    'tb': 1000 ** 4,
    'terabytes': 1000 ** 4,
    'tebibytes': 1024 ** 4,
    'PiB': 1024 ** 5,
    'PB': 1000 ** 5,
    'pB': 1024 ** 5,
    'Pb': 1000 ** 5,
    'pb': 1000 ** 5,
    'petabytes': 1000 ** 5,
    'pebibytes': 1024 ** 5,
    'EiB': 1024 ** 6,
    'EB': 1000 ** 6,
    'eB': 1024 ** 6,
    'Eb': 1000 ** 6,
    'eb': 1000 ** 6,
    'exabytes': 1000 ** 6,
    'exbibytes': 1024 ** 6,
    'ZiB': 1024 ** 7,
    'ZB': 1000 ** 7,
    'zB': 1024 ** 7,
    'Zb': 1000 ** 7,
    'zb': 1000 ** 7,
    'zettabytes': 1000 ** 7,
    'zebibytes': 1024 ** 7,
    'YiB': 1024 ** 8,
    'YB': 1000 ** 8,
    'yB': 1024 ** 8,
    'Yb': 1000 ** 8,
    'yb': 1000 ** 8,
    'yottabytes': 1000 ** 8,
    'yobibytes': 1024 ** 8,
}
