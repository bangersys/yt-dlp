import re
import getpass
import itertools

from ..constants import NO_DEFAULT
from ..cookies import SUPPORTED_BROWSERS, SUPPORTED_KEYRINGS
from ..extractor.adobepass import MSO_INFO
from ..networking.impersonate import ImpersonateTarget
from ..postprocessor import (
    FFmpegExtractAudioPP,
    FFmpegMergerPP,
    FFmpegSubtitlesConvertorPP,
    FFmpegThumbnailsConvertorPP,
    FFmpegVideoConvertorPP,
    FFmpegVideoRemuxerPP,
)
from ..utils import (
    DateRange,
    FormatSorter,
    GeoUtils,
    PlaylistEntries,
    _UnsafeExtensionError,
    download_range_func,
    expand_path,
    float_or_none,
    format_field,
    int_or_none,
    join_nonempty,
    match_filter_func,
    parse_bytes,
    parse_duration,
    shell_quote,
)
from ..YoutubeDL import YoutubeDL
from ..downloader.external import get_external_downloader


def set_compat_opts(opts):
    def _unused_compat_opt(name):
        if name not in opts.compat_opts:
            return False
        opts.compat_opts.discard(name)
        opts.compat_opts.update([f'*{name}'])
        return True

    def set_default_compat(compat_name, opt_name, default=True, remove_compat=True):
        attr = getattr(opts, opt_name)
        if compat_name in opts.compat_opts:
            if attr is None:
                setattr(opts, opt_name, not default)
                return True
            else:
                if remove_compat:
                    _unused_compat_opt(compat_name)
                return False
        elif attr is None:
            setattr(opts, opt_name, default)
        return None

    set_default_compat('abort-on-error', 'ignoreerrors', 'only_download')
    set_default_compat('no-playlist-metafiles', 'allow_playlist_files')
    set_default_compat('no-clean-infojson', 'clean_infojson')
    if 'no-attach-info-json' in opts.compat_opts:
        if opts.embed_infojson:
            _unused_compat_opt('no-attach-info-json')
        else:
            opts.embed_infojson = False
    if 'format-sort' in opts.compat_opts:
        opts.format_sort.extend(FormatSorter.ytdl_default)
    elif 'prefer-vp9-sort' in opts.compat_opts:
        FormatSorter.default = FormatSorter._prefer_vp9_sort

    if 'mtime-by-default' in opts.compat_opts:
        if opts.updatetime is None:
            opts.updatetime = True
        else:
            _unused_compat_opt('mtime-by-default')

    _video_multistreams_set = set_default_compat('multistreams', 'allow_multiple_video_streams', False, remove_compat=False)
    _audio_multistreams_set = set_default_compat('multistreams', 'allow_multiple_audio_streams', False, remove_compat=False)
    if _video_multistreams_set is False and _audio_multistreams_set is False:
        _unused_compat_opt('multistreams')
    if 'filename' in opts.compat_opts:
        if opts.outtmpl.get('default') is None:
            opts.outtmpl.update({'default': '%(title)s-%(id)s.%(ext)s'})
        else:
            _unused_compat_opt('filename')


def validate_options(opts):
    def validate(cndn, name, value=None, msg=None):
        if cndn:
            return True
        raise ValueError((msg or 'invalid {name} "{value}" given').format(name=name, value=value))

    def validate_in(name, value, items, msg=None):
        return validate(value is None or value in items, name, value, msg)

    def validate_regex(name, value, regex):
        return validate(value is None or re.match(regex, value), name, value)

    def validate_positive(name, value, strict=False):
        return validate(value is None or value > 0 or (not strict and value == 0),
                        name, value, '{name} "{value}" must be positive' + ('' if strict else ' or 0'))

    def validate_minmax(min_val, max_val, min_name, max_name=None):
        if max_val is None or min_val is None or max_val >= min_val:
            return
        if not max_name:
            min_name, max_name = f'min {min_name}', f'max {min_name}'
        raise ValueError(f'{max_name} "{max_val}" must be must be greater than or equal to {min_name} "{min_val}"')

    # Usernames and passwords
    validate(sum(map(bool, (opts.usenetrc, opts.netrc_cmd, opts.username))) <= 1, '.netrc',
             msg='{name}, netrc command and username/password are mutually exclusive options')
    validate(opts.password is None or opts.username is not None, 'account username', msg='{name} missing')
    validate(opts.ap_password is None or opts.ap_username is not None,
             'TV Provider account username', msg='{name} missing')
    validate_in('TV Provider', opts.ap_mso, MSO_INFO,
                'Unsupported {name} "{value}", use --ap-list-mso to get a list of supported TV Providers')

    # Numbers
    validate_positive('autonumber start', opts.autonumber_start)
    validate_positive('autonumber size', opts.autonumber_size, True)
    validate_positive('concurrent fragments', opts.concurrent_fragment_downloads, True)
    validate_positive('playlist start', opts.playliststart, True)
    if opts.playlistend != -1:
        validate_minmax(opts.playliststart, opts.playlistend, 'playlist start', 'playlist end')

    # Time ranges
    validate_positive('subtitles sleep interval', opts.sleep_interval_subtitles)
    validate_positive('requests sleep interval', opts.sleep_interval_requests)
    validate_positive('sleep interval', opts.sleep_interval)
    validate_positive('max sleep interval', opts.max_sleep_interval)
    if opts.sleep_interval is None:
        validate(
            opts.max_sleep_interval is None, 'min sleep interval',
            msg='{name} must be specified; use --min-sleep-interval')
    elif opts.max_sleep_interval is None:
        opts.max_sleep_interval = opts.sleep_interval
    else:
        validate_minmax(opts.sleep_interval, opts.max_sleep_interval, 'sleep interval')

    if opts.wait_for_video is not None:
        min_wait, max_wait, *_ = map(parse_duration, [*opts.wait_for_video.split('-', 1), None])
        validate(min_wait is not None and not (max_wait is None and '-' in opts.wait_for_video),
                 'time range to wait for video', opts.wait_for_video)
        validate_minmax(min_wait, max_wait, 'time range to wait for video')
        opts.wait_for_video = (min_wait, max_wait)

    # Format sort
    for f in opts.format_sort:
        validate_regex('format sorting', f, FormatSorter.regex)

    # Postprocessor formats
    if opts.convertsubtitles == 'none':
        opts.convertsubtitles = None
    if opts.convertthumbnails == 'none':
        opts.convertthumbnails = None

    validate_regex('merge output format', opts.merge_output_format,
                   r'({0})(/({0}))*'.format('|'.join(map(re.escape, FFmpegMergerPP.SUPPORTED_EXTS))))
    validate_regex('audio format', opts.audioformat, FFmpegExtractAudioPP.FORMAT_RE)
    validate_in('subtitle format', opts.convertsubtitles, FFmpegSubtitlesConvertorPP.SUPPORTED_EXTS)
    validate_regex('thumbnail format', opts.convertthumbnails, FFmpegThumbnailsConvertorPP.FORMAT_RE)
    validate_regex('recode video format', opts.recodevideo, FFmpegVideoConvertorPP.FORMAT_RE)
    validate_regex('remux video format', opts.remuxvideo, FFmpegVideoRemuxerPP.FORMAT_RE)
    if opts.audioquality:
        opts.audioquality = opts.audioquality.strip('k').strip('K')
        # int_or_none prevents inf, nan
        validate_positive('audio quality', int_or_none(float_or_none(opts.audioquality), default=0))

    # Retries
    def parse_retries(name, value):
        if value is None:
            return None
        elif value in ('inf', 'infinite'):
            return float('inf')
        try:
            int_value = int(value)
        except (TypeError, ValueError):
            validate(False, f'{name} retry count', value)
        validate_positive(f'{name} retry count', int_value)
        return int_value

    opts.retries = parse_retries('download', opts.retries)
    opts.fragment_retries = parse_retries('fragment', opts.fragment_retries)
    opts.extractor_retries = parse_retries('extractor', opts.extractor_retries)
    opts.file_access_retries = parse_retries('file access', opts.file_access_retries)

    # Retry sleep function
    def parse_sleep_func(expr):
        NUMBER_RE = r'\d+(?:\.\d+)?'
        op, start, limit, step, *_ = (*tuple(re.fullmatch(
            rf'(?:(linear|exp)=)?({NUMBER_RE})(?::({NUMBER_RE})?)?(?::({NUMBER_RE}))?',
            expr.strip()).groups()), None, None)

        if op == 'exp':
            return lambda n: min(float(start) * (float(step or 2) ** n), float(limit or 'inf'))
        else:
            default_step = start if op or limit else 0
            return lambda n: min(float(start) + float(step or default_step) * n, float(limit or 'inf'))

    for key, expr in opts.retry_sleep.items():
        if not expr:
            del opts.retry_sleep[key]
            continue
        try:
            opts.retry_sleep[key] = parse_sleep_func(expr)
        except AttributeError:
            raise ValueError(f'invalid {key} retry sleep expression {expr!r}')

    # Bytes
    def validate_bytes(name, value, strict_positive=False):
        if value is None:
            return None
        numeric_limit = parse_bytes(value)
        validate(numeric_limit is not None, name, value)
        if strict_positive:
            validate_positive(name, numeric_limit, True)
        return numeric_limit

    opts.ratelimit = validate_bytes('rate limit', opts.ratelimit, True)
    opts.throttledratelimit = validate_bytes('throttled rate limit', opts.throttledratelimit)
    opts.min_filesize = validate_bytes('min filesize', opts.min_filesize)
    opts.max_filesize = validate_bytes('max filesize', opts.max_filesize)
    opts.buffersize = validate_bytes('buffer size', opts.buffersize, True)
    opts.http_chunk_size = validate_bytes('http chunk size', opts.http_chunk_size)

    # Output templates
    def validate_outtmpl(tmpl, msg):
        err = YoutubeDL.validate_outtmpl(tmpl)
        if err:
            raise ValueError(f'invalid {msg} "{tmpl}": {err}')

    for k, tmpl in opts.outtmpl.items():
        validate_outtmpl(tmpl, f'{k} output template')
    for type_, tmpl_list in opts.forceprint.items():
        for tmpl in tmpl_list:
            validate_outtmpl(tmpl, f'{type_} print template')
    for type_, tmpl_list in opts.print_to_file.items():
        for tmpl, file in tmpl_list:
            validate_outtmpl(tmpl, f'{type_} print to file template')
            validate_outtmpl(file, f'{type_} print to file filename')
    validate_outtmpl(opts.sponsorblock_chapter_title, 'SponsorBlock chapter title')
    for k, tmpl in opts.progress_template.items():
        k = f'{k[:-6]} console title' if '-title' in k else f'{k} progress'
        validate_outtmpl(tmpl, f'{k} template')

    outtmpl_default = opts.outtmpl.get('default')
    if outtmpl_default == '':
        opts.skip_download = None
        del opts.outtmpl['default']

    def parse_chapters(name, value, advanced=False):
        parse_timestamp = lambda x: float('inf') if x in ('inf', 'infinite') else parse_duration(x)
        TIMESTAMP_RE = r'''(?x)(?:
            (?P<start_sign>-?)(?P<start>[^-]+)
        )?\s*-\s*(?:
            (?P<end_sign>-?)(?P<end>[^-]+)
        )?'''

        chapters, ranges, from_url = [], [], False
        for regex in value or []:
            if advanced and regex == '*from-url':
                from_url = True
                continue
            elif not regex.startswith('*'):
                try:
                    chapters.append(re.compile(regex))
                except re.error as err:
                    raise ValueError(f'invalid {name} regex "{regex}" - {err}')
                continue

            for range_ in map(str.strip, regex[1:].split(',')):
                mobj = range_ != '-' and re.fullmatch(TIMESTAMP_RE, range_)
                dur = mobj and [parse_timestamp(mobj.group('start') or '0'), parse_timestamp(mobj.group('end') or 'inf')]
                signs = mobj and (mobj.group('start_sign'), mobj.group('end_sign'))

                err = None
                if None in (dur or [None]):
                    err = 'Must be of the form "*start-end"'
                elif not advanced and any(signs):
                    err = 'Negative timestamps are not allowed'
                else:
                    dur[0] *= -1 if signs[0] else 1
                    dur[1] *= -1 if signs[1] else 1
                    if dur[1] == float('-inf'):
                        err = '"-inf" is not a valid end'
                if err:
                    raise ValueError(f'invalid {name} time range "{regex}". {err}')
                ranges.append(dur)

        return chapters, ranges, from_url

    opts.remove_chapters, opts.remove_ranges, _ = parse_chapters('--remove-chapters', opts.remove_chapters)
    opts.download_ranges = download_range_func(*parse_chapters('--download-sections', opts.download_ranges, True))

    # Cookies from browser
    if opts.cookiesfrombrowser:
        container = None
        mobj = re.fullmatch(r'''(?x)
            (?P<name>[^+:]+)
            (?:\s*\+\s*(?P<keyring>[^:]+))?
            (?:\s*:\s*(?!:)(?P<profile>.+?))?
            (?:\s*::\s*(?P<container>.+))?
        ''', opts.cookiesfrombrowser)
        if mobj is None:
            raise ValueError(f'invalid cookies from browser arguments: {opts.cookiesfrombrowser}')
        browser_name, keyring, profile, container = mobj.group('name', 'keyring', 'profile', 'container')
        browser_name = browser_name.lower()
        if browser_name not in SUPPORTED_BROWSERS:
            raise ValueError(f'unsupported browser specified for cookies: "{browser_name}". '
                             f'Supported browsers are: {", ".join(sorted(SUPPORTED_BROWSERS))}')
        if keyring is not None:
            keyring = keyring.upper()
            if keyring not in SUPPORTED_KEYRINGS:
                raise ValueError(f'unsupported keyring specified for cookies: "{keyring}". '
                                 f'Supported keyrings are: {", ".join(sorted(SUPPORTED_KEYRINGS))}')
        opts.cookiesfrombrowser = (browser_name, profile, keyring, container)

    if opts.impersonate is not None:
        opts.impersonate = ImpersonateTarget.from_str(opts.impersonate.lower())

    # MetadataParser
    def metadataparser_actions(f):
        from ..postprocessor import MetadataFromFieldPP, MetadataParserPP
        if isinstance(f, str):
            cmd = f'--parse-metadata {shell_quote(f)}'
            try:
                actions = [MetadataFromFieldPP.to_action(f)]
            except Exception as err:
                raise ValueError(f'{cmd} is invalid; {err}')
        else:
            cmd = f'--replace-in-metadata {shell_quote(f)}'
            actions = ((MetadataParserPP.Actions.REPLACE, x, *f[1:]) for x in f[0].split(','))

        for action in actions:
            try:
                MetadataParserPP.validate_action(*action)
            except Exception as err:
                raise ValueError(f'{cmd} is invalid; {err}')
            yield action

    if opts.metafromtitle is not None:
        opts.parse_metadata.setdefault('pre_process', []).append(f'title:{opts.metafromtitle}')
    opts.parse_metadata = {
        k: list(itertools.chain(*map(metadataparser_actions, v)))
        for k, v in opts.parse_metadata.items()
    }

    # Other options
    opts.plugin_dirs = opts.plugin_dirs
    if opts.plugin_dirs is None:
        opts.plugin_dirs = ['default']

    if opts.playlist_items is not None:
        try:
            tuple(PlaylistEntries.parse_playlist_items(opts.playlist_items))
        except Exception as err:
            raise ValueError(f'Invalid playlist-items {opts.playlist_items!r}: {err}')

    opts.geo_bypass_country, opts.geo_bypass_ip_block = None, None
    if opts.geo_bypass.lower() not in ('default', 'never'):
        try:
            GeoUtils.random_ipv4(opts.geo_bypass)
        except Exception:
            raise ValueError(f'Unsupported --xff "{opts.geo_bypass}"')
        if len(opts.geo_bypass) == 2:
            opts.geo_bypass_country = opts.geo_bypass
        else:
            opts.geo_bypass_ip_block = opts.geo_bypass
    opts.geo_bypass = opts.geo_bypass.lower() != 'never'

    opts.match_filter = match_filter_func(opts.match_filter, opts.breaking_match_filter)

    if opts.download_archive is not None:
        opts.download_archive = expand_path(opts.download_archive)

    if opts.ffmpeg_location is not None:
        opts.ffmpeg_location = expand_path(opts.ffmpeg_location)

    if opts.user_agent is not None:
        opts.headers.setdefault('User-Agent', opts.user_agent)
    if opts.referer is not None:
        opts.headers.setdefault('Referer', opts.referer)

    if opts.no_sponsorblock:
        opts.sponsorblock_mark = opts.sponsorblock_remove = set()

    default_downloader = None
    for proto, path in opts.external_downloader.items():
        if path == 'native':
            continue
        ed = get_external_downloader(path)
        if ed is None:
            raise ValueError(
                f'No such {format_field(proto, None, "%s ", ignore="default")}external downloader "{path}"')
        elif ed and proto == 'default':
            default_downloader = ed.get_basename()

    for policy in opts.color.values():
        if policy not in ('always', 'auto', 'auto-tty', 'no_color', 'no_color-tty', 'never'):
            raise ValueError(f'"{policy}" is not a valid color policy')

    warnings, deprecation_warnings = [], []

    # Common mistake: -f best
    if opts.format == 'best':
        warnings.append('.\n         '.join((
            '"-f best" selects the best pre-merged format which is often not the best option',
            'To let yt-dlp download and merge the best available formats, simply do not pass any format selection',
            'If you know what you are doing and want only the best pre-merged format, use "-f b" instead to suppress this warning')))

    # Common mistake: -f mp4
    if opts.format == 'mp4':
        warnings.append('.\n         '.join((
            '"-f mp4" selects the best pre-merged mp4 format which is often not what\'s intended',
            'Pre-merged mp4 formats are not available from all sites, or may only be available in lower quality',
            'To prioritize the best h264 video and aac audio in an mp4 container, use "-t mp4" instead',
            'If you know what you are doing and want a pre-merged mp4 format, use "-f b[ext=mp4]" instead to suppress this warning')))

    # --(postprocessor/downloader)-args without name
    def report_args_compat(name, value, key1, key2=None, where=None):
        if key1 in value and key2 not in value:
            warnings.append(f'{name.title()} arguments given without specifying name. '
                            f'The arguments will be given to {where or f"all {name}s"}')
            return True
        return False

    if report_args_compat('external downloader', opts.external_downloader_args,
                          'default', where=default_downloader) and default_downloader:
        # Compat with youtube-dl's behavior. See https://github.com/ytdl-org/youtube-dl/commit/49c5293014bc11ec8c009856cd63cffa6296c1e1
        opts.external_downloader_args.setdefault(default_downloader, opts.external_downloader_args.pop('default'))

    if report_args_compat('post-processor', opts.postprocessor_args, 'default-compat', 'default'):
        opts.postprocessor_args['default'] = opts.postprocessor_args.pop('default-compat')

    def report_conflict(arg1, opt1, arg2='--allow-unplayable-formats', opt2='allow_unplayable_formats',
                        val1=NO_DEFAULT, val2=NO_DEFAULT, default=False):
        if val2 is NO_DEFAULT:
            val2 = getattr(opts, opt2)
        if not val2:
            return

        if val1 is NO_DEFAULT:
            val1 = getattr(opts, opt1)
        if val1:
            warnings.append(f'{arg1} is ignored since {arg2} was given')
        setattr(opts, opt1, default)

    # Conflicting options
    report_conflict('--playlist-reverse', 'playlist_reverse', '--playlist-random', 'playlist_random')
    report_conflict('--playlist-reverse', 'playlist_reverse', '--lazy-playlist', 'lazy_playlist')
    report_conflict('--playlist-random', 'playlist_random', '--lazy-playlist', 'lazy_playlist')
    report_conflict('--dateafter', 'dateafter', '--date', 'date', default=None)
    report_conflict('--datebefore', 'datebefore', '--date', 'date', default=None)
    report_conflict('--exec-before-download', 'exec_before_dl_cmd',
                    '"--exec before_dl:"', 'exec_cmd', val2=opts.exec_cmd.get('before_dl'))
    report_conflict('--id', 'useid', '--output', 'outtmpl', val2=opts.outtmpl.get('default'))
    report_conflict('--remux-video', 'remuxvideo', '--recode-video', 'recodevideo')

    # Conflicts with --allow-unplayable-formats
    report_conflict('--embed-metadata', 'addmetadata')
    report_conflict('--embed-chapters', 'addchapters')
    report_conflict('--embed-info-json', 'embed_infojson')
    report_conflict('--embed-subs', 'embedsubtitles')
    report_conflict('--embed-thumbnail', 'embedthumbnail')
    report_conflict('--extract-audio', 'extractaudio')
    report_conflict('--fixup', 'fixup', val1=opts.fixup not in (None, 'never', 'ignore'), default='never')
    report_conflict('--recode-video', 'recodevideo')
    report_conflict('--remove-chapters', 'remove_chapters', default=[])
    report_conflict('--remux-video', 'remuxvideo')
    report_conflict('--sponsorblock-remove', 'sponsorblock_remove', default=set())
    report_conflict('--xattrs', 'xattrs')

    if hasattr(opts, '_deprecated_options'):
        deprecation_warnings.append(
            f'The following options have been deprecated: {", ".join(opts._deprecated_options)}\n'
            'Please remove them from your command/configuration to avoid future errors.\n'
            'See  https://github.com/yt-dlp/yt-dlp/issues/14198  for more details')
        del opts._deprecated_options

    # Dependent options
    opts.date = DateRange.day(opts.date) if opts.date else DateRange(opts.dateafter, opts.datebefore)

    if opts.exec_before_dl_cmd:
        opts.exec_cmd['before_dl'] = opts.exec_before_dl_cmd

    if opts.useid:  # --id is not deprecated in youtube-dl
        opts.outtmpl['default'] = '%(id)s.%(ext)s'

    if opts.overwrites:  # --force-overwrites implies --no-continue
        opts.continue_dl = False

    if (opts.addmetadata or opts.sponsorblock_mark) and opts.addchapters is None:
        # Add chapters when adding metadata or marking sponsors
        opts.addchapters = True

    if opts.extractaudio and not opts.keepvideo and opts.format is None:
        # Do not unnecessarily download audio
        opts.format = 'bestaudio/best'

    if opts.getcomments and opts.writeinfojson is None and not opts.embed_infojson:
        # If JSON is not printed anywhere, but comments are requested, save it to file
        if not opts.dumpjson or opts.print_json or opts.dump_single_json:
            opts.writeinfojson = True

    if opts.allsubtitles and not (opts.embedsubtitles or opts.writeautomaticsub):
        # --all-sub automatically sets --write-sub if --write-auto-sub is not given
        opts.writesubtitles = True

    if opts.addmetadata and opts.embed_infojson is None:
        # If embedding metadata and infojson is present, embed it
        opts.embed_infojson = 'if_exists'

    # Ask for passwords
    if opts.username is not None and opts.password is None:
        opts.password = getpass.getpass('Type account password and press [Return]: ')
    if opts.ap_username is not None and opts.ap_password is None:
        opts.ap_password = getpass.getpass('Type TV provider account password and press [Return]: ')

    # compat option changes global state destructively; only allow from cli
    if 'allow-unsafe-ext' in opts.compat_opts:
        warnings.append(
            'Using allow-unsafe-ext opens you up to potential attacks. '
            'Use with great care!')
        _UnsafeExtensionError.sanitize_extension = lambda x, prepend=False: x

    return warnings, deprecation_warnings
