from __future__ import annotations

"""Shared type definitions used across the yt-dlp codebase.

This module intentionally contains lightweight aliases and ``TypedDict``
definitions only, so it can be imported safely from any package layer without
introducing circular dependencies.
"""

from typing import Any, TypedDict


HTTPHeaders = dict[str, str]


class Thumbnail(TypedDict, total=False):
    url: str
    id: str
    width: int
    height: int
    resolution: str
    preference: int


class Subtitle(TypedDict, total=False):
    url: str
    ext: str
    name: str
    data: str
    id: str
    quality: int


class Chapter(TypedDict, total=False):
    start_time: float
    end_time: float
    title: str


class Fragment(TypedDict, total=False):
    url: str
    duration: float


class Format(TypedDict, total=False):
    format_id: str
    format_note: str
    ext: str
    url: str
    manifest_url: str
    tbr: float
    asr: float
    fps: float
    width: int
    height: int
    vcodec: str
    acodec: str
    vbr: float
    abr: float
    filesize: int
    filesize_approx: int
    container: str
    protocol: str
    language: str
    language_preference: int
    preference: int
    quality: int
    dynamic_range: str
    video_ext: str
    audio_ext: str
    http_headers: HTTPHeaders


class InfoDict(TypedDict, total=False):
    id: str
    title: str
    url: str
    ext: str
    alt_title: str
    description: str
    display_id: str
    thumbnails: list[Thumbnail]
    thumbnail: str

    duration: float
    duration_string: str
    upload_date: str
    timestamp: int
    release_date: str
    release_timestamp: int
    modified_date: str
    modified_timestamp: int

    uploader: str
    uploader_id: str
    uploader_url: str
    channel: str
    channel_id: str
    channel_url: str
    channel_follower_count: int
    channel_is_verified: bool
    location: str
    creator: str
    artist: str
    track: str
    album: str
    composer: str
    genre: str

    view_count: int
    concurrent_view_count: int
    like_count: int
    dislike_count: int
    repost_count: int
    average_rating: float
    comment_count: int
    save_count: int

    age_limit: int
    live_status: str
    is_live: bool
    was_live: bool
    playable_in_embed: bool
    availability: str
    media_type: str

    formats: list[Format]
    subtitles: dict[str, list[Subtitle]]
    automatic_captions: dict[str, list[Subtitle]]
    chapters: list[Chapter]
    fragments: list[Fragment]
    heatmap: list[dict[str, Any]]

    webpage_url: str
    webpage_url_basename: str
    webpage_url_domain: str
    extractor: str
    extractor_key: str
    playlist: str
    playlist_index: int
    playlist_id: str
    playlist_title: str
    playlist_uploader: str
    playlist_uploader_id: str

    requested_formats: list[Format]
    requested_subtitles: dict[str, list[Subtitle]]


__all__ = [
    'HTTPHeaders',
    'Thumbnail',
    'Subtitle',
    'Chapter',
    'Fragment',
    'Format',
    'InfoDict',
]
