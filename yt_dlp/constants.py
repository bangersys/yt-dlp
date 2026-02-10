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
