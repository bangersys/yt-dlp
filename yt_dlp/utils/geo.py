import random
import socket
import struct

from .exceptions import ExtractorError
from ..constants import COUNTRY_IP_MAP, COUNTRY_MAP


class GeoRestrictedError(ExtractorError):
    """Geographic restriction Error exception.

    This exception may be thrown when a video is not available from your
    geographic location due to geographic restrictions imposed by a website.
    """

    def __init__(self, msg, countries=None, **kwargs):
        kwargs['expected'] = True
        super().__init__(msg, **kwargs)
        self.countries = countries


class ISO3166Utils:
    """
    Utility class for ISO 3166 country codes.
    Research Note: Used to map 2-letter country codes to full country names.
    This is often used in error messages when a video is restricted to specific regions.
    """
    # From http://data.okfn.org/data/core/country-list
    _country_map = COUNTRY_MAP

    @classmethod
    def short2full(cls, code):
        """Convert an ISO 3166-2 country code to the corresponding full name"""
        return cls._country_map.get(code.upper())


class GeoUtils:
    """
    Utility class for geo-bypass operations.
    Research Note: This class stores a mapping of 2-letter country codes to major IPv4 address blocks.
    These blocks are used to generate random IP addresses that are sent in the 'X-Forwarded-For' 
    header to spoof the client's geographic location.
    """
    _country_ip_map = COUNTRY_IP_MAP

    @classmethod
    def random_ipv4(cls, code_or_block):
        """
        Generates a random IPv4 address within a specified country's IP range or a CIDR block.
        Research Note: This is the core engine for geographic location spoofing. By choosing a random
        IP from a known country block, yt-dlp makes the server believe the request originated from that country.
        """
        if len(code_or_block) == 2:
            block = cls._country_ip_map.get(code_or_block.upper())
            if not block:
                return None
        else:
            block = code_or_block
        addr, preflen = block.split('/')
        addr_min = struct.unpack('!L', socket.inet_aton(addr))[0]
        addr_max = addr_min | (0xffffffff >> int(preflen))
        return str(socket.inet_ntoa(
            struct.pack('!L', random.randint(addr_min, addr_max))))


def initialize_geo_bypass(geo_bypass_context, get_param, write_debug, is_geo_bypassable=True, x_forwarded_for_ip=None):
    """
    Initializes the geo-bypass mechanism for a video extraction.
    Research Note: This function decides which country or IP block to use for spoofing based on
    user parameters (--geo-bypass-country, --geo-bypass-ip-block) and extractor preferences (_GEO_COUNTRIES).
    It populates the 'X-Forwarded-For' IP used in subsequent requests.
    """
    if x_forwarded_for_ip:
        return x_forwarded_for_ip

    # Geo bypass mechanism is explicitly disabled by user
    if not get_param('geo_bypass', True):
        return None

    if not geo_bypass_context:
        geo_bypass_context = {}

    # Backward compatibility: previously _initialize_geo_bypass
    # expected a list of countries, some 3rd party code may still use
    # it this way
    if isinstance(geo_bypass_context, (list, tuple)):
        geo_bypass_context = {
            'countries': geo_bypass_context,
        }

    # Path 1: bypassing based on IP block in CIDR notation
    ip_block = get_param('geo_bypass_ip_block', None)
    if not ip_block:
        ip_blocks = geo_bypass_context.get('ip_blocks')
        if is_geo_bypassable and ip_blocks:
            ip_block = random.choice(ip_blocks)

    if ip_block:
        x_forwarded_for_ip = GeoUtils.random_ipv4(ip_block)
        write_debug(f'Using fake IP {x_forwarded_for_ip} as X-Forwarded-For')
        return x_forwarded_for_ip

    # Path 2: bypassing based on country code
    country = get_param('geo_bypass_country', None)
    if not country:
        countries = geo_bypass_context.get('countries')
        if is_geo_bypassable and countries:
            country = random.choice(countries)

    if country:
        x_forwarded_for_ip = GeoUtils.random_ipv4(country)
        write_debug(f'Using fake IP {x_forwarded_for_ip} ({country.upper()}) as X-Forwarded-For')

    return x_forwarded_for_ip


def maybe_fake_ip_and_retry(countries, get_param, is_geo_bypassable, x_forwarded_for_ip, report_warning, write_debug):
    """
    Checks if a retry with a spoofed IP is warranted after a GeoRestrictedError.
    Research Note: This is an automatic recovery mechanism. If extraction fails due to geo-restriction,
    yt-dlp can optionally pick a random allowed country and try faking an IP from that region.
    """
    if (not get_param('geo_bypass_country', None)
            and is_geo_bypassable
            and get_param('geo_bypass', True)
            and not x_forwarded_for_ip
            and countries):
        country_code = random.choice(countries)
        new_ip = GeoUtils.random_ipv4(country_code)
        if new_ip:
            report_warning(
                'Video is geo restricted. Retrying extraction with fake IP '
                f'{new_ip} ({country_code.upper()}) as X-Forwarded-For.')
            return new_ip
    return None


def raise_geo_restricted(msg='This video is not available from your location due to geo restriction',
                         countries=None, metadata_available=False, get_param=None, report_warning=None):
    """
    Raises a GeoRestrictedError with appropriate metadata.
    Research Note: This is how extractors signal they've detected a geographic block. 
    It carries 'countries', a list of region codes where the content IS available.
    """
    if metadata_available and get_param and (
            get_param('ignore_no_formats_error') or get_param('wait_for_video')):
        if report_warning:
            report_warning(msg)
    else:
        raise GeoRestrictedError(msg, countries=countries)


def geo_verification_headers(get_param):
    """
    Returns headers required for geo-verification proxies.
    Research Note: Some sites require a specific proxy to verify the user's location.
    This function handles the 'Ytdl-request-proxy' header which tells the downloader
    to route the verification request through the specified proxy.
    """
    headers = {}
    geo_verification_proxy = get_param('geo_verification_proxy')
    if geo_verification_proxy:
        headers['Ytdl-request-proxy'] = geo_verification_proxy
    return headers
