import sys
import os
import collections
import itertools
import traceback
import getpass
import optparse

from ..constants import SEARCH_EXAMPLES, POSTPROCESS_WHEN
from ..globals import IN_CLI, plugin_dirs, supported_js_runtimes, supported_remote_components

from .options import parseOpts
from .validation import set_compat_opts, validate_options


def _exit(status=0, *args):
    for msg in args:
        sys.stderr.write(msg)
    raise SystemExit(status)


def get_urls(urls, batchfile, verbose):
    """
    @param verbose      -1: quiet, 0: normal, 1: verbose
    """
    from ..utils import expand_path, preferredencoding, read_batch_urls, read_stdin, write_string
    batch_urls = []
    if batchfile is not None:
        try:
            batch_urls = read_batch_urls(
                read_stdin(None if verbose == -1 else 'URLs') if batchfile == '-'
                else open(expand_path(batchfile), encoding='utf-8', errors='ignore'))
            if verbose == 1:
                write_string('[debug] Batch file urls: ' + repr(batch_urls) + '\n')
        except OSError:
            _exit(f'ERROR: batch file {batchfile} could not be read')
    _enc = preferredencoding()
    return [
        url.strip().decode(_enc, 'ignore') if isinstance(url, bytes) else url.strip()
        for url in batch_urls + urls]


def print_extractor_information(opts, urls):
    from ..extractor import list_extractor_classes
    from ..extractor.adobepass import MSO_INFO
    from ..utils import render_table, write_string
    out = ''
    if opts.list_extractors:
        # Importing GenericIE is currently slow since it imports YoutubeIE
        from ..extractor.generic import GenericIE

        urls = dict.fromkeys(urls, False)
        for ie in list_extractor_classes(opts.age_limit):
            out += ie.IE_NAME + (' (CURRENTLY BROKEN)' if not ie.working() else '') + '\n'
            if ie == GenericIE:
                matched_urls = [url for url, matched in urls.items() if not matched]
            else:
                matched_urls = tuple(filter(ie.suitable, urls.keys()))
                urls.update(dict.fromkeys(matched_urls, True))
            out += ''.join(f'  {url}\n' for url in matched_urls)
    elif opts.list_extractor_descriptions:
        out = '\n'.join(
            ie.description(markdown=False, search_examples=SEARCH_EXAMPLES)
            for ie in list_extractor_classes(opts.age_limit) if ie.working() and ie.IE_DESC is not False)
    elif opts.ap_list_mso:
        out = 'Supported TV Providers:\n{}\n'.format(render_table(
            ['mso', 'mso name'],
            [[mso_id, mso_info['name']] for mso_id, mso_info in MSO_INFO.items()]))
    else:
        return False
    write_string(out, out=sys.stdout)
    return True


def get_postprocessors(opts):
    yield from opts.add_postprocessors

    for when, actions in opts.parse_metadata.items():
        yield {
            'key': 'MetadataParser',
            'actions': actions,
            'when': when,
        }
    sponsorblock_query = opts.sponsorblock_mark | opts.sponsorblock_remove
    if sponsorblock_query:
        yield {
            'key': 'SponsorBlock',
            'categories': sponsorblock_query,
            'api': opts.sponsorblock_api,
            'when': 'after_filter',
        }
    if opts.convertsubtitles:
        yield {
            'key': 'FFmpegSubtitlesConvertor',
            'format': opts.convertsubtitles,
            'when': 'before_dl',
        }
    if opts.convertthumbnails:
        yield {
            'key': 'FFmpegThumbnailsConvertor',
            'format': opts.convertthumbnails,
            'when': 'before_dl',
        }
    if opts.extractaudio:
        yield {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': opts.audioformat,
            'preferredquality': opts.audioquality,
            'nopostoverwrites': opts.nopostoverwrites,
        }
    if opts.remuxvideo:
        yield {
            'key': 'FFmpegVideoRemuxer',
            'preferedformat': opts.remuxvideo,
        }
    if opts.recodevideo:
        yield {
            'key': 'FFmpegVideoConvertor',
            'preferedformat': opts.recodevideo,
        }
    # If ModifyChapters is going to remove chapters, subtitles must already be in the container.
    if opts.embedsubtitles:
        keep_subs = 'no-keep-subs' not in opts.compat_opts
        yield {
            'key': 'FFmpegEmbedSubtitle',
            # already_have_subtitle = True prevents the file from being deleted after embedding
            'already_have_subtitle': opts.writesubtitles and keep_subs,
        }
        if not opts.writeautomaticsub and keep_subs:
            opts.writesubtitles = True

    # ModifyChapters must run before FFmpegMetadataPP
    if opts.remove_chapters or sponsorblock_query:
        yield {
            'key': 'ModifyChapters',
            'remove_chapters_patterns': opts.remove_chapters,
            'remove_sponsor_segments': opts.sponsorblock_remove,
            'remove_ranges': opts.remove_ranges,
            'sponsorblock_chapter_title': opts.sponsorblock_chapter_title,
            'force_keyframes': opts.force_keyframes_at_cuts,
        }
    # FFmpegMetadataPP should be run after FFmpegVideoConvertorPP and
    # FFmpegExtractAudioPP as containers before conversion may not support
    # metadata (3gp, webm, etc.)
    # By default ffmpeg preserves metadata applicable for both
    # source and target containers. From this point the container won't change,
    # so metadata can be added here.
    if opts.addmetadata or opts.addchapters or opts.embed_infojson:
        yield {
            'key': 'FFmpegMetadata',
            'add_chapters': opts.addchapters,
            'add_metadata': opts.addmetadata,
            'add_infojson': opts.embed_infojson,
        }
    if opts.embedthumbnail:
        yield {
            'key': 'EmbedThumbnail',
            # already_have_thumbnail = True prevents the file from being deleted after embedding
            'already_have_thumbnail': opts.writethumbnail,
        }
        if not opts.writethumbnail:
            opts.writethumbnail = True
            opts.outtmpl['pl_thumbnail'] = ''
    if opts.split_chapters:
        yield {
            'key': 'FFmpegSplitChapters',
            'force_keyframes': opts.force_keyframes_at_cuts,
        }
    # XAttrMetadataPP should be run after post-processors that may change file contents
    if opts.xattrs:
        yield {'key': 'XAttrMetadata'}
    if opts.concat_playlist != 'never':
        yield {
            'key': 'FFmpegConcat',
            'only_multi_video': opts.concat_playlist != 'always',
            'when': 'playlist',
        }
    # Exec must be the last PP of each category
    for when, exec_cmd in opts.exec_cmd.items():
        yield {
            'key': 'Exec',
            'exec_cmd': exec_cmd,
            'when': when,
        }


ParsedOptions = collections.namedtuple('ParsedOptions', ('parser', 'options', 'urls', 'ydl_opts'))


def parse_options(argv=None):
    """@returns ParsedOptions(parser, opts, urls, ydl_opts)"""
    from ..utils import variadic
    from ..YoutubeDL import YoutubeDL
    parser, opts, urls = parseOpts(argv)
    urls = get_urls(urls, opts.batchfile, -1 if opts.quiet and not opts.verbose else opts.verbose)

    set_compat_opts(opts)
    try:
        warnings, deprecation_warnings = validate_options(opts)
    except ValueError as err:
        parser.error(f'{err}\n')

    postprocessors = list(get_postprocessors(opts))

    print_only = bool(opts.forceprint) and all(k not in opts.forceprint for k in POSTPROCESS_WHEN[3:])
    any_getting = any(getattr(opts, k) for k in (
        'dumpjson', 'dump_single_json', 'getdescription', 'getduration', 'getfilename',
        'getformat', 'getid', 'getthumbnail', 'gettitle', 'geturl',
    ))
    if opts.quiet is None:
        opts.quiet = any_getting or opts.print_json or bool(opts.forceprint)

    playlist_pps = [pp for pp in postprocessors if pp.get('when') == 'playlist']
    write_playlist_infojson = (opts.writeinfojson and not opts.clean_infojson
                               and opts.allow_playlist_files and opts.outtmpl.get('pl_infojson') != '')
    if not any((
        opts.extract_flat,
        opts.dump_single_json,
        opts.forceprint.get('playlist'),
        opts.print_to_file.get('playlist'),
        write_playlist_infojson,
    )):
        if not playlist_pps:
            opts.extract_flat = 'discard'
        elif playlist_pps == [{'key': 'FFmpegConcat', 'only_multi_video': True, 'when': 'playlist'}]:
            opts.extract_flat = 'discard_in_playlist'

    final_ext = (
        opts.recodevideo if opts.recodevideo in FFmpegVideoConvertorPP.SUPPORTED_EXTS
        else opts.remuxvideo if opts.remuxvideo in FFmpegVideoRemuxerPP.SUPPORTED_EXTS
        else opts.audioformat if (opts.extractaudio and opts.audioformat in FFmpegExtractAudioPP.SUPPORTED_EXTS)
        else None)

    js_runtimes = {
        runtime.lower(): {'path': path} for runtime, path in (
            [*arg.split(':', 1), None][:2] for arg in opts.js_runtimes)}

    return ParsedOptions(parser, opts, urls, {
        'usenetrc': opts.usenetrc,
        'netrc_location': opts.netrc_location,
        'netrc_cmd': opts.netrc_cmd,
        'username': opts.username,
        'password': opts.password,
        'twofactor': opts.twofactor,
        'videopassword': opts.videopassword,
        'ap_mso': opts.ap_mso,
        'ap_username': opts.ap_username,
        'ap_password': opts.ap_password,
        'client_certificate': opts.client_certificate,
        'client_certificate_key': opts.client_certificate_key,
        'client_certificate_password': opts.client_certificate_password,
        'quiet': opts.quiet,
        'no_warnings': opts.no_warnings,
        'forceurl': opts.geturl,
        'forcetitle': opts.gettitle,
        'forceid': opts.getid,
        'forcethumbnail': opts.getthumbnail,
        'forcedescription': opts.getdescription,
        'forceduration': opts.getduration,
        'forcefilename': opts.getfilename,
        'forceformat': opts.getformat,
        'forceprint': opts.forceprint,
        'print_to_file': opts.print_to_file,
        'forcejson': opts.dumpjson or opts.print_json,
        'dump_single_json': opts.dump_single_json,
        'force_write_download_archive': opts.force_write_download_archive,
        'simulate': (print_only or any_getting or None) if opts.simulate is None else opts.simulate,
        'skip_download': opts.skip_download,
        'format': opts.format,
        'allow_unplayable_formats': opts.allow_unplayable_formats,
        'ignore_no_formats_error': opts.ignore_no_formats_error,
        'format_sort': opts.format_sort,
        'format_sort_force': opts.format_sort_force,
        'allow_multiple_video_streams': opts.allow_multiple_video_streams,
        'allow_multiple_audio_streams': opts.allow_multiple_audio_streams,
        'check_formats': opts.check_formats,
        'listformats': opts.listformats,
        'listformats_table': opts.listformats_table,
        'outtmpl': opts.outtmpl,
        'outtmpl_na_placeholder': opts.outtmpl_na_placeholder,
        'paths': opts.paths,
        'autonumber_size': opts.autonumber_size,
        'autonumber_start': opts.autonumber_start,
        'restrictfilenames': opts.restrictfilenames,
        'windowsfilenames': opts.windowsfilenames,
        'ignoreerrors': opts.ignoreerrors,
        'force_generic_extractor': opts.force_generic_extractor,
        'allowed_extractors': opts.allowed_extractors or ['default'],
        'ratelimit': opts.ratelimit,
        'throttledratelimit': opts.throttledratelimit,
        'overwrites': opts.overwrites,
        'retries': opts.retries,
        'file_access_retries': opts.file_access_retries,
        'fragment_retries': opts.fragment_retries,
        'extractor_retries': opts.extractor_retries,
        'retry_sleep_functions': opts.retry_sleep,
        'skip_unavailable_fragments': opts.skip_unavailable_fragments,
        'keep_fragments': opts.keep_fragments,
        'concurrent_fragment_downloads': opts.concurrent_fragment_downloads,
        'buffersize': opts.buffersize,
        'noresizebuffer': opts.noresizebuffer,
        'http_chunk_size': opts.http_chunk_size,
        'continuedl': opts.continue_dl,
        'noprogress': opts.quiet if opts.noprogress is None else opts.noprogress,
        'progress_with_newline': opts.progress_with_newline,
        'progress_template': opts.progress_template,
        'progress_delta': opts.progress_delta,
        'playliststart': opts.playliststart,
        'playlistend': opts.playlistend,
        'playlistreverse': opts.playlist_reverse,
        'playlistrandom': opts.playlist_random,
        'lazy_playlist': opts.lazy_playlist,
        'noplaylist': opts.noplaylist,
        'logtostderr': opts.outtmpl.get('default') == '-',
        'consoletitle': opts.consoletitle,
        'nopart': opts.nopart,
        'updatetime': opts.updatetime,
        'writedescription': opts.writedescription,
        'writeinfojson': opts.writeinfojson,
        'allow_playlist_files': opts.allow_playlist_files,
        'clean_infojson': opts.clean_infojson,
        'getcomments': opts.getcomments,
        'writethumbnail': opts.writethumbnail is True,
        'write_all_thumbnails': opts.writethumbnail == 'all',
        'writelink': opts.writelink,
        'writeurllink': opts.writeurllink,
        'writewebloclink': opts.writewebloclink,
        'writedesktoplink': opts.writedesktoplink,
        'writesubtitles': opts.writesubtitles,
        'writeautomaticsub': opts.writeautomaticsub,
        'allsubtitles': opts.allsubtitles,
        'listsubtitles': opts.listsubtitles,
        'subtitlesformat': opts.subtitlesformat,
        'subtitleslangs': opts.subtitleslangs,
        'matchtitle': opts.matchtitle,
        'rejecttitle': opts.rejecttitle,
        'max_downloads': opts.max_downloads,
        'prefer_free_formats': opts.prefer_free_formats,
        'trim_file_name': opts.trim_file_name,
        'verbose': opts.verbose,
        'dump_intermediate_pages': opts.dump_intermediate_pages,
        'write_pages': opts.write_pages,
        'load_pages': opts.load_pages,
        'test': opts.test,
        'keepvideo': opts.keepvideo,
        'min_filesize': opts.min_filesize,
        'max_filesize': opts.max_filesize,
        'min_views': opts.min_views,
        'max_views': opts.max_views,
        'daterange': opts.date,
        'cachedir': opts.cachedir,
        'age_limit': opts.age_limit,
        'download_archive': opts.download_archive,
        'break_on_existing': opts.break_on_existing,
        'break_on_reject': opts.break_on_reject,
        'break_per_url': opts.break_per_url,
        'skip_playlist_after_errors': opts.skip_playlist_after_errors,
        'cookiefile': opts.cookiefile,
        'cookiesfrombrowser': opts.cookiesfrombrowser,
        'legacyserverconnect': opts.legacy_server_connect,
        'nocheckcertificate': opts.no_check_certificate,
        'prefer_insecure': opts.prefer_insecure,
        'enable_file_urls': opts.enable_file_urls,
        'http_headers': opts.headers,
        'proxy': opts.proxy,
        'socket_timeout': opts.socket_timeout,
        'bidi_workaround': opts.bidi_workaround,
        'debug_printtraffic': opts.debug_printtraffic,
        'default_search': opts.default_search,
        'dynamic_mpd': opts.dynamic_mpd,
        'extractor_args': opts.extractor_args,
        'encoding': opts.encoding,
        'extract_flat': opts.extract_flat,
        'live_from_start': opts.live_from_start,
        'wait_for_video': opts.wait_for_video,
        'mark_watched': opts.mark_watched,
        'merge_output_format': opts.merge_output_format,
        'final_ext': final_ext,
        'postprocessors': postprocessors,
        'fixup': opts.fixup,
        'source_address': opts.source_address,
        'impersonate': opts.impersonate,
        'sleep_interval_requests': opts.sleep_interval_requests,
        'sleep_interval': opts.sleep_interval,
        'max_sleep_interval': opts.max_sleep_interval,
        'sleep_interval_subtitles': opts.sleep_interval_subtitles,
        'external_downloader': opts.external_downloader,
        'download_ranges': opts.download_ranges,
        'force_keyframes_at_cuts': opts.force_keyframes_at_cuts,
        'list_thumbnails': opts.list_thumbnails,
        'playlist_items': opts.playlist_items,
        'match_filter': opts.match_filter,
        'color': opts.color,
        'ffmpeg_location': opts.ffmpeg_location,
        'hls_prefer_native': opts.hls_prefer_native,
        'hls_use_mpegts': opts.hls_use_mpegts,
        'hls_split_discontinuity': opts.hls_split_discontinuity,
        'external_downloader_args': opts.external_downloader_args,
        'postprocessor_args': opts.postprocessor_args,
        'geo_verification_proxy': opts.geo_verification_proxy,
        'geo_bypass': opts.geo_bypass,
        'geo_bypass_country': opts.geo_bypass_country,
        'geo_bypass_ip_block': opts.geo_bypass_ip_block,
        'useid': opts.useid or None,
        'js_runtimes': js_runtimes,
        'remote_components': opts.remote_components,
        'warn_when_outdated': opts.update_self is None,
        '_warnings': warnings,
        '_deprecation_warnings': deprecation_warnings,
        'compat_opts': opts.compat_opts,
    })


def _real_main(argv=None):
    from ..plugins import load_all_plugins as _load_all_plugins
    from ..update import Updater
    from ..utils import DownloadCancelled, setproctitle
    from ..YoutubeDL import YoutubeDL
    from ..postprocessor import FFmpegPostProcessor
    setproctitle('yt-dlp')

    parser, opts, all_urls, ydl_opts = parse_options(argv)

    if print_extractor_information(opts, all_urls):
        return

    # We may need ffmpeg_location without having access to the YoutubeDL instance
    # See https://github.com/yt-dlp/yt-dlp/issues/2191
    if opts.ffmpeg_location:
        FFmpegPostProcessor._ffmpeg_location.set(opts.ffmpeg_location)

    # load all plugins into the global lookup
    plugin_dirs.value = opts.plugin_dirs
    if plugin_dirs.value:
        _load_all_plugins()

    with YoutubeDL(ydl_opts) as ydl:
        pre_process = opts.update_self or opts.rm_cachedir
        actual_use = all_urls or opts.load_info_filename

        if opts.rm_cachedir:
            ydl.cache.remove()

        try:
            updater = Updater(ydl, opts.update_self)
            if opts.update_self and updater.update() and actual_use and updater.cmd:
                return updater.restart()
        except Exception:
            traceback.print_exc()
            ydl._download_retcode = 100

        if opts.list_impersonate_targets:
            from ..networking.impersonate import ImpersonateTarget
            from ..utils import join_nonempty, render_table
            known_targets = [
                # List of simplified targets we know are supported,
                # to help users know what dependencies may be required.
                (ImpersonateTarget('chrome'), 'curl_cffi'),
                (ImpersonateTarget('safari'), 'curl_cffi'),
                (ImpersonateTarget('firefox'), 'curl_cffi>=0.10'),
                (ImpersonateTarget('edge'), 'curl_cffi'),
                (ImpersonateTarget('tor'), 'curl_cffi>=0.11'),
            ]

            available_targets = ydl._get_available_impersonate_targets()

            def make_row(target, handler):
                return [
                    join_nonempty(target.client.title(), target.version, delim='-') or '-',
                    join_nonempty((target.os or '').title(), target.os_version, delim='-') or '-',
                    handler,
                ]

            rows = [make_row(target, handler) for target, handler in available_targets]

            for known_target, known_handler in known_targets:
                if not any(
                    known_target in target and known_handler.startswith(handler)
                    for target, handler in available_targets
                ):
                    rows.insert(0, [
                        ydl._format_out(text, ydl.Styles.SUPPRESS)
                        for text in make_row(known_target, f'{known_handler} (unavailable)')
                    ])

            ydl.to_screen('[info] Available impersonate targets')
            ydl.to_stdout(render_table(['Client', 'OS', 'Source'], rows, extra_gap=2, delim='-'))
            return

        if not actual_use:
            if pre_process:
                return ydl._download_retcode

            args = sys.argv[1:] if argv is None else argv
            ydl.warn_if_short_id(args)

            # Show a useful error message and wait for keypress if not launched from shell on Windows
            if not args and os.name == 'nt' and getattr(sys, 'frozen', False):
                import ctypes.wintypes
                import msvcrt

                kernel32 = ctypes.WinDLL('Kernel32')

                buffer = (1 * ctypes.wintypes.DWORD)()
                attached_processes = kernel32.GetConsoleProcessList(buffer, 1)
                # If we only have a single process attached, then the executable was double clicked
                # When using `pyinstaller` with `--onefile`, two processes get attached
                is_onefile = hasattr(sys, '_MEIPASS') and os.path.basename(sys._MEIPASS).startswith('_MEI')
                if attached_processes == 1 or (is_onefile and attached_processes == 2):
                    print(parser._generate_error_message(
                        'Do not double-click the executable, instead call it from a command line.\n'
                        'Please read the README for further information on how to use yt-dlp: '
                        'https://github.com/yt-dlp/yt-dlp#readme'))
                    msvcrt.getch()
                    _exit(2)
            parser.error(
                'You must provide at least one URL.\n'
                'Type yt-dlp --help to see a list of all options.')

        parser.destroy()
        try:
            if opts.load_info_filename is not None:
                if all_urls:
                    ydl.report_warning('URLs are ignored due to --load-info-json')
                return ydl.download_with_info_file(expand_path(opts.load_info_filename))
            else:
                return ydl.download(all_urls)
        except DownloadCancelled:
            ydl.to_screen('Aborting remaining downloads')
            return 101


def main(argv=None):
    from ..utils._jsruntime import (
        BunJsRuntime as _BunJsRuntime,
        DenoJsRuntime as _DenoJsRuntime,
        NodeJsRuntime as _NodeJsRuntime,
        QuickJsRuntime as _QuickJsRuntime,
    )
    IN_CLI.value = True

    # Register JS runtimes and remote components
    supported_js_runtimes.value['deno'] = _DenoJsRuntime
    supported_js_runtimes.value['node'] = _NodeJsRuntime
    supported_js_runtimes.value['bun'] = _BunJsRuntime
    supported_js_runtimes.value['quickjs'] = _QuickJsRuntime

    supported_remote_components.value.append('ejs:github')
    supported_remote_components.value.append('ejs:npm')

    from ..cookies import CookieLoadError
    from ..utils import DownloadError, SameFileError, variadic
    try:
        _exit(*variadic(_real_main(argv)))
    except (CookieLoadError, DownloadError):
        _exit(1)
    except SameFileError as e:
        _exit(f'ERROR: {e}')
    except KeyboardInterrupt:
        _exit('\nERROR: Interrupted by user')
    except BrokenPipeError as e:
        # https://docs.python.org/3/library/signal.html#note-on-sigpipe
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        _exit(f'\nERROR: {e}')
    except optparse.OptParseError as e:
        _exit(2, f'\n{e}')
