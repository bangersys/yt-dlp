import re

from .json import NO_DEFAULT


class download_range_func:
    def __init__(self, chapters, ranges, from_info=False):
        self.chapters, self.ranges, self.from_info = chapters, ranges, from_info

    def __call__(self, info_dict, ydl):
        warning = ('There are no chapters matching the regex' if info_dict.get('chapters')
                   else 'Cannot match chapters since chapter information is unavailable')
        for regex in self.chapters or []:
            for i, chapter in enumerate(info_dict.get('chapters') or []):
                if re.search(regex, chapter['title']):
                    warning = None
                    yield {**chapter, 'index': i}
        if self.chapters and warning:
            ydl.to_screen(f'[info] {info_dict["id"]}: {warning}')

        for start, end in self.ranges or []:
            yield {
                'start_time': self._handle_negative_timestamp(start, info_dict),
                'end_time': self._handle_negative_timestamp(end, info_dict),
            }

        if self.from_info and (info_dict.get('start_time') or info_dict.get('end_time')):
            yield {
                'start_time': info_dict.get('start_time') or 0,
                'end_time': info_dict.get('end_time') or float('inf'),
            }
        elif not self.ranges and not self.chapters:
            yield {}

    @staticmethod
    def _handle_negative_timestamp(time, info):
        return max(info['duration'] + time, 0) if info.get('duration') and time < 0 else time

    def __eq__(self, other):
        return (isinstance(other, download_range_func)
                and self.chapters == other.chapters and self.ranges == other.ranges)

    def __repr__(self):
        return f'{__name__}.{type(self).__name__}({self.chapters}, {self.ranges})'
