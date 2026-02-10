"""Project-wide constants.

This module centralizes immutable values that are shared across multiple
submodules to keep related definitions in one place and reduce duplication.
"""

import collections.abc
import itertools
import re
import types


def IDENTITY(x):
    """Identity function."""
    return x


class NO_DEFAULT:
    """Sentinel for missing defaults."""
    pass


class Namespace(types.SimpleNamespace):
    def __iter__(self):
        return iter(self.__dict__.values())

    def __getitem__(self, key):
        return self.__dict__[key]

    def __contains__(self, key):
        return key in self.__dict__

    @property
    def items_(self):
        return self.__dict__.items()


# Regex Constants
PACKED_CODES_RE = r"}\('(.+)',(\d+),(\d+),'([^']+)'\.split\('\|'\)"
NUMBER_RE = r'\d+(?:\.\d+)?'
JSON_LD_RE = r'(?is)<script[^>]+type=(["\']?)application/ld\+json\1[^>]*>\s*(?P<json_ld>{.+?}|\[.+?\])\s*</script>'

STR_FORMAT_RE_TMPL = r'''(?x)
    (?<!%)(?P<prefix>(?:%%)*)
    %
    (?P<has_key>\((?P<key>{0})\))?
    (?P<format>
        (?P<conversion>[#0\-+ ]+)?
        (?P<min_width>\d+)?
        (?P<precision>\.\d+)?
        (?P<len_mod>[hlL])?  # unused in python
        {1}  # conversion type
    )
'''
STR_FORMAT_TYPES = 'diouxXeEfFgGcrsa'

# Age Rating Constants
US_RATINGS = {
    'G': 0,
    'PG': 10,
    'PG-13': 13,
    'R': 16,
    'NC': 18,
}

TV_PARENTAL_GUIDELINES = {
    'TV-Y': 0,
    'TV-Y7': 7,
    'TV-G': 0,
    'TV-PG': 0,
    'TV-14': 14,
    'TV-MA': 17,
}

# Output & Post-processing Constants
POSTPROCESS_WHEN = ('pre_process', 'after_filter', 'video', 'before_dl', 'post_process', 'after_move', 'after_video', 'playlist')

DEFAULT_OUTTMPL = {
    'default': '%(title)s [%(id)s].%(ext)s',
    'chapter': '%(title)s - %(section_number)03d %(section_title)s [%(id)s].%(ext)s',
}

OUTTMPL_TYPES = {
    'chapter': None,
    'subtitle': None,
    'thumbnail': None,
    'description': 'description',
    'annotation': 'annotations.xml',
    'infojson': 'info.json',
    'link': None,
    'pl_video': None,
    'pl_thumbnail': None,
    'pl_description': 'description',
    'pl_infojson': 'info.json',
}

# File & Metadata Constants
BOMS = [
    (b'\xef\xbb\xbf', 'utf-8'),
    (b'\x00\x00\xfe\xff', 'utf-32-be'),
    (b'\xff\xfe\x00\x00', 'utf-32-le'),
    (b'\xff\xfe', 'utf-16-le'),
    (b'\xfe\xff', 'utf-16-be'),
]

# Shortcut Templates
DOT_URL_LINK_TEMPLATE = '''\
[InternetShortcut]
URL=%(url)s
'''

DOT_WEBLOC_LINK_TEMPLATE = '''\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>URL</key>
\t<string>%(url)s</string>
</dict>
</plist>
'''

DOT_DESKTOP_LINK_TEMPLATE = '''\
[Desktop Entry]
Encoding=UTF-8
Name=%(filename)s
Type=Link
URL=%(url)s
Icon=text-html
'''

LINK_TEMPLATES = {
    'url': DOT_URL_LINK_TEMPLATE,
    'desktop': DOT_DESKTOP_LINK_TEMPLATE,
    'webloc': DOT_WEBLOC_LINK_TEMPLATE,
}

# Date & Time Constants
ENGLISH_MONTH_NAMES = (
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December')

MONTH_NAMES = {
    'en': ENGLISH_MONTH_NAMES,
    'fr': [
        'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'],
    'is': [
        'janúar', 'febrúar', 'mars', 'apríl', 'maí', 'júní',
        'júlí', 'ágúst', 'september', 'október', 'nóvember', 'desember'],
    'pl': ['stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca',
           'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia'],
}

TIMEZONE_NAMES = {
    'UT': 0, 'UTC': 0, 'GMT': 0, 'Z': 0,
    'AST': -4, 'ADT': -3,
    'EST': -5, 'EDT': -4,
    'CST': -6, 'CDT': -5,
    'MST': -7, 'MDT': -6,
    'PST': -8, 'PDT': -7,
}

DATE_FORMATS = (
    '%d %B %Y',
    '%d %b %Y',
    '%B %d %Y',
    '%B %dst %Y',
    '%B %dnd %Y',
    '%B %drd %Y',
    '%B %dth %Y',
    '%b %d %Y',
    '%b %dst %Y',
    '%b %dnd %Y',
    '%b %drd %Y',
    '%b %dth %Y',
    '%b %dst %Y %I:%M',
    '%b %dnd %Y %I:%M',
    '%b %drd %Y %I:%M',
    '%b %dth %Y %I:%M',
    '%Y %m %d',
    '%Y-%m-%d',
    '%Y.%m.%d.',
    '%Y/%m/%d',
    '%Y/%m/%d %H:%M',
    '%Y/%m/%d %H:%M:%S',
    '%Y%m%d%H%M',
    '%Y%m%d%H%M%S',
    '%Y%m%d',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S.%f',
    '%Y-%m-%d %H:%M:%S:%f',
    '%d.%m.%Y %H:%M',
    '%d.%m.%Y %H.%M',
    '%Y-%m-%dH%M%SZ',
    '%Y-%m-%dT%H:%M:%SZ',
    '%Y-%m-%dT%H:%M:%S.%fZ',
    '%Y-%m-%dT%H:%M:%S.%f0Z',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M:%S.%f',
    '%Y-%m-%dT%H:%M',
    '%b %d %Y at %H:%M',
    '%b %d %Y at %H:%M:%S',
    '%B %d %Y at %H:%M',
    '%B %d %Y at %H:%M:%S',
    '%H:%M %d-%b-%Y',
)

DATE_FORMATS_DAY_FIRST = list(DATE_FORMATS) + [
    '%d-%m-%Y',
    '%d.%m.%Y',
    '%d.%m.%y',
    '%d/%m/%Y',
    '%d/%m/%y',
    '%d/%m/%Y %H:%M:%S',
    '%d-%m-%Y %H:%M',
    '%H:%M %d/%m/%Y',
]

DATE_FORMATS_MONTH_FIRST = list(DATE_FORMATS) + [
    '%m-%d-%Y',
    '%m.%d.%Y',
    '%m/%d/%Y',
    '%m/%d/%y',
    '%m/%d/%Y %H:%M:%S',
]

# Networking Constants
USER_AGENT_TMPL = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Safari/537.36'
)
CHROME_MAJOR_VERSION_RANGE = (137, 143)

MEDIA_EXTENSIONS = Namespace(
    common_video=('avi', 'flv', 'mkv', 'mov', 'mp4', 'webm'),
    video=('3g2', '3gp', 'f4v', 'mk3d', 'divx', 'mpg', 'ogv', 'm4v', 'wmv'),
    common_audio=('aiff', 'alac', 'flac', 'm4a', 'mka', 'mp3', 'ogg', 'opus', 'wav'),
    audio=('aac', 'ape', 'asf', 'f4a', 'f4b', 'm4b', 'm4r', 'oga', 'ogx', 'spx', 'vorbis', 'wma', 'weba'),
    thumbnails=('jpg', 'png', 'webp'),
    storyboards=('mhtml', ),
    subtitles=('srt', 'vtt', 'ass', 'lrc'),
    manifests=('f4f', 'f4m', 'm3u8', 'smil', 'mpd'),
)
MEDIA_EXTENSIONS.video += MEDIA_EXTENSIONS.common_video
MEDIA_EXTENSIONS.audio += MEDIA_EXTENSIONS.common_audio

KNOWN_EXTENSIONS = (*MEDIA_EXTENSIONS.video, *MEDIA_EXTENSIONS.audio, *MEDIA_EXTENSIONS.manifests)

# Formatting Constants
ACCENT_CHARS = dict(zip('ÂÃÄÀÁÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖŐØŒÙÚÛÜŰÝÞßàáâãäåæçèéêëìíîïðñòóôõöőøœùúûüűýþÿ',
                        itertools.chain('AAAAAA', ['AE'], 'CEEEEIIIIDNOOOOOOO', ['OE'], 'UUUUUY', ['TH', 'ss'],
                                        'aaaaaa', ['ae'], 'ceeeeiiiionooooooo', ['oe'], 'uuuuuy', ['th'], 'y'), strict=True))

# Cookie Constants

# Cookie Constants
CHROMIUM_BASED_BROWSERS = {'brave', 'chrome', 'chromium', 'edge', 'opera', 'vivaldi', 'whale'}
SUPPORTED_BROWSERS = CHROMIUM_BASED_BROWSERS | {'firefox', 'safari'}


class _LinuxDesktopEnvironment(Namespace):
    OTHER = 'other'
    CINNAMON = 'cinnamon'
    DEEPIN = 'deepin'
    GNOME = 'gnome'
    KDE3 = 'kde3'
    KDE4 = 'kde4'
    KDE5 = 'kde5'
    KDE6 = 'kde6'
    PANTHEON = 'pantheon'
    UKUI = 'ukui'
    UNITY = 'unity'
    XFCE = 'xfce'
    LXQT = 'lxqt'


class _LinuxKeyring(Namespace):
    KWALLET = 'kwallet'
    KWALLET5 = 'kwallet5'
    KWALLET6 = 'kwallet6'
    GNOMEKEYRING = 'gnomekeyring'
    BASICTEXT = 'basictext'


SUPPORTED_KEYRINGS = ('kwallet', 'kwallet5', 'kwallet6', 'gnomekeyring', 'basictext')

# Post-processor Constants (FFmpeg)
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


# Geo Constants
COUNTRY_MAP = {
    'AF': 'Afghanistan',
    'AX': 'Åland Islands',
    'AL': 'Albania',
    'DZ': 'Algeria',
    'AS': 'American Samoa',
    'AD': 'Andorra',
    'AO': 'Angola',
    'AI': 'Anguilla',
    'AQ': 'Antarctica',
    'AG': 'Antigua and Barbuda',
    'AR': 'Argentina',
    'AM': 'Armenia',
    'AW': 'Aruba',
    'AU': 'Australia',
    'AT': 'Austria',
    'AZ': 'Azerbaijan',
    'BS': 'Bahamas',
    'BH': 'Bahrain',
    'BD': 'Bangladesh',
    'BB': 'Barbados',
    'BY': 'Belarus',
    'BE': 'Belgium',
    'BZ': 'Belize',
    'BJ': 'Benin',
    'BM': 'Bermuda',
    'BT': 'Bhutan',
    'BO': 'Bolivia, Plurinational State of',
    'BQ': 'Bonaire, Sint Eustatius and Saba',
    'BA': 'Bosnia and Herzegovina',
    'BW': 'Botswana',
    'BV': 'Bouvet Island',
    'BR': 'Brazil',
    'IO': 'British Indian Ocean Territory',
    'BN': 'Brunei Darussalam',
    'BG': 'Bulgaria',
    'BF': 'Burkina Faso',
    'BI': 'Burundi',
    'KH': 'Cambodia',
    'CM': 'Cameroon',
    'CA': 'Canada',
    'CV': 'Cape Verde',
    'KY': 'Cayman Islands',
    'CF': 'Central African Republic',
    'TD': 'Chad',
    'CL': 'Chile',
    'CN': 'China',
    'CX': 'Christmas Island',
    'CC': 'Cocos (Keeling) Islands',
    'CO': 'Colombia',
    'KM': 'Comoros',
    'CG': 'Congo',
    'CD': 'Congo, the Democratic Republic of the',
    'CK': 'Cook Islands',
    'CR': 'Costa Rica',
    'CI': 'Côte d\'Ivoire',
    'HR': 'Croatia',
    'CU': 'Cuba',
    'CW': 'Curaçao',
    'CY': 'Cyprus',
    'CZ': 'Czech Republic',
    'DK': 'Denmark',
    'DJ': 'Djibouti',
    'DM': 'Dominica',
    'DO': 'Dominican Republic',
    'EC': 'Ecuador',
    'EG': 'Egypt',
    'SV': 'El Salvador',
    'GQ': 'Equatorial Guinea',
    'ER': 'Eritrea',
    'EE': 'Estonia',
    'ET': 'Ethiopia',
    'FK': 'Falkland Islands (Malvinas)',
    'FO': 'Faroe Islands',
    'FJ': 'Fiji',
    'FI': 'Finland',
    'FR': 'France',
    'GF': 'French Guiana',
    'PF': 'French Polynesia',
    'TF': 'French Southern Territories',
    'GA': 'Gabon',
    'GM': 'Gambia',
    'GE': 'Georgia',
    'DE': 'Germany',
    'GH': 'Ghana',
    'GI': 'Gibraltar',
    'GR': 'Greece',
    'GL': 'Greenland',
    'GD': 'Grenada',
    'GP': 'Guadeloupe',
    'GU': 'Guam',
    'GT': 'Guatemala',
    'GG': 'Guernsey',
    'GN': 'Guinea',
    'GW': 'Guinea-Bissau',
    'GY': 'Guyana',
    'HT': 'Haiti',
    'HM': 'Heard Island and McDonald Islands',
    'VA': 'Holy See (Vatican City State)',
    'HN': 'Honduras',
    'HK': 'Hong Kong',
    'HU': 'Hungary',
    'IS': 'Iceland',
    'IN': 'India',
    'ID': 'Indonesia',
    'IR': 'Iran, Islamic Republic of',
    'IQ': 'Iraq',
    'IE': 'Ireland',
    'IM': 'Isle of Man',
    'IL': 'Israel',
    'IT': 'Italy',
    'JM': 'Jamaica',
    'JP': 'Japan',
    'JE': 'Jersey',
    'JO': 'Jordan',
    'KZ': 'Kazakhstan',
    'KE': 'Kenya',
    'KI': 'Kiribati',
    'KP': 'Korea, Democratic People\'s Republic of',
    'KR': 'Korea, Republic of',
    'KW': 'Kuwait',
    'KG': 'Kyrgyzstan',
    'LA': 'Lao People\'s Democratic Republic',
    'LV': 'Latvia',
    'LB': 'Lebanon',
    'LS': 'Lesotho',
    'LR': 'Liberia',
    'LY': 'Libya',
    'LI': 'Liechtenstein',
    'LT': 'Lithuania',
    'LU': 'Luxembourg',
    'MO': 'Macao',
    'MK': 'Macedonia, the Former Yugoslav Republic of',
    'MG': 'Madagascar',
    'MW': 'Malawi',
    'MY': 'Malaysia',
    'MV': 'Maldives',
    'ML': 'Mali',
    'MT': 'Malta',
    'MH': 'Marshall Islands',
    'MQ': 'Martinique',
    'MR': 'Mauritania',
    'MU': 'Mauritius',
    'YT': 'Mayotte',
    'MX': 'Mexico',
    'FM': 'Micronesia, Federated States of',
    'MD': 'Moldova, Republic of',
    'MC': 'Monaco',
    'MN': 'Mongolia',
    'ME': 'Montenegro',
    'MS': 'Montserrat',
    'MA': 'Morocco',
    'MZ': 'Mozambique',
    'MM': 'Myanmar',
    'NA': 'Namibia',
    'NR': 'Nauru',
    'NP': 'Nepal',
    'NL': 'Netherlands',
    'NC': 'New Caledonia',
    'NZ': 'New Zealand',
    'NI': 'Nicaragua',
    'NE': 'Niger',
    'NG': 'Nigeria',
    'NU': 'Niue',
    'NF': 'Norfolk Island',
    'MP': 'Northern Mariana Islands',
    'NO': 'Norway',
    'OM': 'Oman',
    'PK': 'Pakistan',
    'PW': 'Palau',
    'PS': 'Palestine, State of',
    'PA': 'Panama',
    'PG': 'Papua New Guinea',
    'PY': 'Paraguay',
    'PE': 'Peru',
    'PH': 'Philippines',
    'PN': 'Pitcairn',
    'PL': 'Poland',
    'PT': 'Portugal',
    'PR': 'Puerto Rico',
    'QA': 'Qatar',
    'RE': 'Réunion',
    'RO': 'Romania',
    'RU': 'Russian Federation',
    'RW': 'Rwanda',
    'BL': 'Saint Barthélemy',
    'SH': 'Saint Helena, Ascension and Tristan da Cunha',
    'KN': 'Saint Kitts and Nevis',
    'LC': 'Saint Lucia',
    'MF': 'Saint Martin (French part)',
    'PM': 'Saint Pierre and Miquelon',
    'VC': 'Saint Vincent and the Grenadines',
    'WS': 'Samoa',
    'SM': 'San Marino',
    'ST': 'Sao Tome and Principe',
    'SA': 'Saudi Arabia',
    'SN': 'Senegal',
    'RS': 'Serbia',
    'SC': 'Seychelles',
    'SL': 'Sierra Leone',
    'SG': 'Singapore',
    'SX': 'Sint Maarten (Dutch part)',
    'SK': 'Slovakia',
    'SI': 'Slovenia',
    'SB': 'Solomon Islands',
    'SO': 'Somalia',
    'ZA': 'South Africa',
    'GS': 'South Georgia and the South Sandwich Islands',
    'SS': 'South Sudan',
    'ES': 'Spain',
    'LK': 'Sri Lanka',
    'SD': 'Sudan',
    'SR': 'Suriname',
    'SJ': 'Svalbard and Jan Mayen',
    'SZ': 'Swaziland',
    'SE': 'Sweden',
    'CH': 'Switzerland',
    'SY': 'Syrian Arab Republic',
    'TW': 'Taiwan, Province of China',
    'TJ': 'Tajikistan',
    'TZ': 'Tanzania, United Republic of',
    'TH': 'Thailand',
    'TL': 'Timor-Leste',
    'TG': 'Togo',
    'TK': 'Tokelau',
    'TO': 'Tonga',
    'TT': 'Trinidad and Tobago',
    'TN': 'Tunisia',
    'TR': 'Turkey',
    'TM': 'Turkmenistan',
    'TC': 'Turks and Caicos Islands',
    'TV': 'Tuvalu',
    'UG': 'Uganda',
    'UA': 'Ukraine',
    'AE': 'United Arab Emirates',
    'GB': 'United Kingdom',
    'US': 'United States',
    'UM': 'United States Minor Outlying Islands',
    'UY': 'Uruguay',
    'UZ': 'Uzbekistan',
    'OH': 'Western Sahara',
    'EH': 'Western Sahara',
    'YE': 'Yemen',
    'ZM': 'Zambia',
    'ZW': 'Zimbabwe',
    'AP': 'Asia/Pacific Region',
    'EU': 'Europe',
}

COUNTRY_IP_MAP = {
    'AD': '46.172.224.0/19',
    'AE': '94.200.0.0/13',
    'AF': '149.54.0.0/17',
    'AG': '209.59.64.0/18',
    'AI': '204.14.248.0/21',
    'AL': '46.99.0.0/16',
    'AM': '46.70.0.0/15',
    'AO': '105.168.0.0/13',
    'AP': '182.50.184.0/21',
    'AQ': '23.154.160.0/24',
    'AR': '181.0.0.0/12',
    'AS': '202.70.112.0/20',
    'AT': '77.116.0.0/14',
    'AU': '1.128.0.0/11',
    'AW': '181.41.0.0/18',
    'AX': '185.217.4.0/22',
    'AZ': '5.197.0.0/16',
    'BA': '31.176.128.0/17',
    'BB': '65.48.128.0/17',
    'BD': '114.130.0.0/16',
    'BE': '57.0.0.0/8',
    'BF': '102.178.0.0/15',
    'BG': '95.42.0.0/15',
    'BH': '37.131.0.0/17',
    'BI': '154.117.192.0/18',
    'BJ': '137.255.0.0/16',
    'BL': '185.212.72.0/23',
    'BM': '196.12.64.0/18',
    'BN': '156.31.0.0/16',
    'BO': '161.56.0.0/16',
    'BQ': '161.0.80.0/20',
    'BR': '191.128.0.0/12',
    'BS': '24.51.64.0/18',
    'BT': '119.2.96.0/19',
    'BW': '168.167.0.0/16',
    'BY': '178.120.0.0/13',
    'BZ': '179.42.192.0/18',
    'CA': '99.224.0.0/11',
    'CD': '41.243.0.0/16',
    'CF': '197.242.176.0/21',
    'CG': '160.113.0.0/16',
    'CH': '85.0.0.0/13',
    'CI': '102.136.0.0/14',
    'CK': '202.65.32.0/19',
    'CL': '152.172.0.0/14',
    'CM': '102.244.0.0/14',
    'CN': '36.128.0.0/10',
    'CO': '181.240.0.0/12',
    'CR': '201.192.0.0/12',
    'CU': '152.206.0.0/15',
    'CV': '165.90.96.0/19',
    'CW': '190.88.128.0/17',
    'CY': '31.153.0.0/16',
    'CZ': '88.100.0.0/14',
    'DE': '53.0.0.0/8',
    'DJ': '197.241.0.0/17',
    'DK': '87.48.0.0/12',
    'DM': '192.243.48.0/20',
    'DO': '152.166.0.0/15',
    'DZ': '41.96.0.0/12',
    'EC': '186.68.0.0/15',
    'EE': '90.190.0.0/15',
    'EG': '156.160.0.0/11',
    'ER': '196.200.96.0/20',
    'ES': '88.0.0.0/11',
    'ET': '196.188.0.0/14',
    'EU': '2.16.0.0/13',
    'FI': '91.152.0.0/13',
    'FJ': '144.120.0.0/16',
    'FK': '80.73.208.0/21',
    'FM': '119.252.112.0/20',
    'FO': '88.85.32.0/19',
    'FR': '90.0.0.0/9',
    'GA': '41.158.0.0/15',
    'GB': '25.0.0.0/8',
    'GD': '74.122.88.0/21',
    'GE': '31.146.0.0/16',
    'GF': '161.22.64.0/18',
    'GG': '62.68.160.0/19',
    'GH': '154.160.0.0/12',
    'GI': '95.164.0.0/16',
    'GL': '88.83.0.0/19',
    'GM': '160.182.0.0/15',
    'GN': '197.149.192.0/18',
    'GP': '104.250.0.0/19',
    'GQ': '105.235.224.0/20',
    'GR': '94.64.0.0/13',
    'GT': '168.234.0.0/16',
    'GU': '168.123.0.0/16',
    'GW': '197.214.80.0/20',
    'GY': '181.41.64.0/18',
    'HK': '113.252.0.0/14',
    'HN': '181.210.0.0/16',
    'HR': '93.136.0.0/13',
    'HT': '148.102.128.0/17',
    'HU': '84.0.0.0/14',
    'ID': '39.192.0.0/10',
    'IE': '87.32.0.0/12',
    'IL': '79.176.0.0/13',
    'IM': '5.62.80.0/20',
    'IN': '117.192.0.0/10',
    'IO': '203.83.48.0/21',
    'IQ': '37.236.0.0/14',
    'IR': '2.176.0.0/12',
    'IS': '82.221.0.0/16',
    'IT': '79.0.0.0/10',
    'JE': '87.244.64.0/18',
    'JM': '72.27.0.0/17',
    'JO': '176.29.0.0/16',
    'JP': '133.0.0.0/8',
    'KE': '105.48.0.0/12',
    'KG': '158.181.128.0/17',
    'KH': '36.37.128.0/17',
    'KI': '103.25.140.0/22',
    'KM': '197.255.224.0/20',
    'KN': '198.167.192.0/19',
    'KP': '175.45.176.0/22',
    'KR': '175.192.0.0/10',
    'KW': '37.36.0.0/14',
    'KY': '64.96.0.0/15',
    'KZ': '2.72.0.0/13',
    'LA': '115.84.64.0/18',
    'LB': '178.135.0.0/16',
    'LC': '24.92.144.0/20',
    'LI': '82.117.0.0/19',
    'LD': '112.134.0.0/15',
    'LK': '112.134.0.0/15',
    'LR': '102.183.0.0/16',
    'LS': '129.232.0.0/17',
    'LT': '78.56.0.0/13',
    'LU': '188.42.0.0/16',
    'LV': '46.109.0.0/16',
    'LY': '41.252.0.0/14',
    'MA': '105.128.0.0/11',
    'MC': '88.209.64.0/18',
    'MD': '37.246.0.0/16',
    'ME': '178.175.0.0/17',
    'MF': '74.112.232.0/21',
    'MG': '154.126.0.0/17',
    'MH': '117.103.88.0/21',
    'MK': '77.28.0.0/15',
    'ML': '154.118.128.0/18',
    'MM': '37.111.0.0/17',
    'MN': '49.0.128.0/17',
    'MO': '60.246.0.0/16',
    'MP': '202.88.64.0/20',
    'MQ': '109.203.224.0/19',
    'MR': '41.188.64.0/18',
    'MS': '208.90.112.0/22',
    'MT': '46.11.0.0/16',
    'MU': '105.16.0.0/12',
    'MV': '27.114.128.0/18',
    'MW': '102.70.0.0/15',
    'MX': '187.192.0.0/11',
    'MY': '175.136.0.0/13',
    'MZ': '197.218.0.0/15',
    'NA': '41.182.0.0/16',
    'NC': '101.101.0.0/18',
    'NE': '197.214.0.0/18',
    'NF': '203.17.240.0/22',
    'NG': '105.112.0.0/12',
    'NI': '186.76.0.0/15',
    'NL': '145.96.0.0/11',
    'NO': '84.208.0.0/13',
    'NP': '36.252.0.0/15',
    'NR': '203.98.224.0/19',
    'NU': '49.156.48.0/22',
    'NZ': '49.224.0.0/14',
    'OM': '5.36.0.0/15',
    'PA': '186.72.0.0/15',
    'PE': '186.160.0.0/14',
    'PF': '123.50.64.0/18',
    'PG': '124.240.192.0/19',
    'PH': '49.144.0.0/13',
    'PK': '39.32.0.0/11',
    'PL': '83.0.0.0/11',
    'PM': '70.36.0.0/20',
    'PR': '66.50.0.0/16',
    'PS': '188.161.0.0/16',
    'PT': '85.240.0.0/13',
    'PW': '202.124.224.0/20',
    'PY': '181.120.0.0/14',
    'QA': '37.210.0.0/15',
    'RE': '102.35.0.0/16',
    'RO': '79.112.0.0/13',
    'RS': '93.86.0.0/15',
    'RU': '5.136.0.0/13',
    'RW': '41.186.0.0/16',
    'SA': '188.48.0.0/13',
    'SB': '202.1.160.0/19',
    'SC': '154.192.0.0/11',
    'SD': '102.120.0.0/13',
    'SE': '78.64.0.0/12',
    'SG': '8.128.0.0/10',
    'SI': '188.196.0.0/14',
    'SK': '78.98.0.0/15',
    'SL': '102.143.0.0/17',
    'SM': '89.186.32.0/19',
    'SN': '41.82.0.0/15',
    'SO': '154.115.192.0/18',
    'SR': '186.179.128.0/17',
    'SS': '105.235.208.0/21',
    'ST': '197.159.160.0/19',
    'SV': '168.243.0.0/16',
    'SX': '190.102.0.0/20',
    'SY': '5.0.0.0/16',
    'SZ': '41.84.224.0/19',
    'TC': '65.255.48.0/20',
    'TD': '154.68.128.0/19',
    'TG': '196.168.0.0/14',
    'TH': '171.96.0.0/13',
    'TJ': '85.9.128.0/18',
    'TK': '27.96.24.0/21',
    'TL': '180.189.160.0/20',
    'TM': '95.85.96.0/19',
    'TN': '197.0.0.0/11',
    'TO': '175.176.144.0/21',
    'TR': '78.160.0.0/11',
    'TT': '186.44.0.0/15',
    'TV': '202.2.96.0/19',
    'TW': '120.96.0.0/11',
    'TZ': '156.156.0.0/14',
    'UA': '37.52.0.0/14',
    'UG': '102.80.0.0/13',
    'US': '6.0.0.0/8',
    'UY': '167.56.0.0/13',
    'UZ': '84.54.64.0/18',
    'VA': '212.77.0.0/19',
    'VC': '207.191.240.0/21',
    'VE': '186.88.0.0/13',
    'VG': '66.81.192.0/20',
    'VI': '146.226.0.0/16',
    'VN': '14.160.0.0/11',
    'VU': '202.80.32.0/20',
    'WF': '117.20.32.0/21',
    'WS': '202.4.32.0/19',
    'YE': '134.35.0.0/16',
    'YT': '41.242.116.0/22',
    'ZA': '41.0.0.0/11',
    'ZM': '102.144.0.0/13',
    'ZW': '102.177.192.0/18',
}

# Internal Searches
YTDL_PATH_RE = re.compile(r'youtube_dl')
PREFERRED_SEARCH_IE = {
    'ytsearch': 'YouTube',
    'ytsearchdate': 'YouTube',
    'ytsr': 'YouTube',
    'scsearch': 'SoundCloud',
    'scsearchall': 'SoundCloud',
    'gvsearch': 'Google Video',
    'yvsearch': 'Yahoo Video',
}

# Shell Quoting Constants
CMD_QUOTE_TRANS = {
    # Keep quotes balanced by replacing them with `""` instead of `\\"`
    ord('"'): '""',
    # These require an env-variable `=` containing `"^\n\n"` (set in `utils.Popen`)
    # `=` should be unique since variables containing `=` cannot be set using cmd
    ord('\n'): '%=%',
    ord('\r'): '%=%',
    # Use zero length variable replacement so `%` doesn't get expanded
    # `cd` is always set as long as extensions are enabled (`/E:ON` in `utils.Popen`)
    ord('%'): '%%cd:~,%',
}
WINDOWS_QUOTE_TRANS = {ord('"'): R'\"'}


# File Size Constants
FILE_SIZE_UNITS = {
    'B': 1,
    'b': 1,
    'byte': 1,
    'bytes': 1,
    'KB': 1000,
    'kilobyte': 1000,
    'kilobytes': 1000,
    'KiB': 1024,
    'kibibyte': 1024,
    'kibibytes': 1024,
    'MB': 1000**2,
    'megabyte': 1000**2,
    'megabytes': 1000**2,
    'MiB': 1024**2,
    'mebibyte': 1024**2,
    'mebibytes': 1024**2,
    'GB': 1000**3,
    'gigabyte': 1000**3,
    'gigabytes': 1000**3,
    'GiB': 1024**3,
    'gibibyte': 1024**3,
    'gibibytes': 1024**3,
    'TB': 1000**4,
    'terabyte': 1000**4,
    'terabytes': 1000**4,
    'TiB': 1024**4,
    'tebibyte': 1024**4,
    'tebibytes': 1024**4,
    'PB': 1000**5,
    'petabyte': 1000**5,
    'petabytes': 1000**5,
    'PiB': 1024**5,
    'pebibyte': 1024**5,
    'pebibytes': 1024**5,
    'EB': 1000**6,
    'exabyte': 1000**6,
    'exabytes': 1000**6,
    'EiB': 1024**6,
    'exbibyte': 1024**6,
    'exbibytes': 1024**6,
    'ZB': 1000**7,
    'zettabyte': 1000**7,
    'zettabytes': 1000**7,
    'ZiB': 1024**7,
    'zebibyte': 1024**7,
    'zebibytes': 1024**7,
    'YB': 1000**8,
    'yottabyte': 1000**8,
    'yottabytes': 1000**8,
    'YiB': 1024**8,
    'yobibyte': 1024**8,
    'yobibytes': 1024**8,
}

# Update Constants
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

SEARCH_EXAMPLES = ('cute kittens', 'slithering pythons', 'falling cat', 'angry poodle', 'purple fish', 'running tortoise', 'sleeping bunny', 'burping cow')


# Downloader Constants
class ProgressStyles(Namespace):
    DEFAULT = 'default'
    QUIET = 'quiet'
    NO_PROGRESS = 'no_progress'


# YoutubeDL (Internal) Constants
_SEARCHES = {
    'ytsearch': 'YouTube',
    'ytsearchall': 'YouTube',
    'ytsearchdate': 'YouTube',
    'ytsr': 'YouTube',
    'scsearch': 'SoundCloud',
    'scsearchall': 'SoundCloud',
    'gvsearch': 'Google Video',
    'yvsearch': 'Yahoo Video',
}
