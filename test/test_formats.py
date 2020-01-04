import fnmatch
import os
from unittest import TestCase

from modules.detectors import MiDetector, FfmpegDetector
from modules.ffmpeg import Ffmpeg
from modules.formats import FileFormat, FILE_FORMAT_SUPPORTED_TRACK_TYPES, FILE_FORMAT_FILENAME_WILDCARDS


class TestFormats(TestCase):
    # https://standaloneinstaller.com/blog/big-list-of-sample-videos-for-testers-124.html
    def list_samples(self):
        formats_found = set()
        for root, directories, files in os.walk(os.path.join(os.path.dirname(__file__), 'samples')):
            for filename in files:
                match = False
                for wildcard, file_format in FILE_FORMAT_FILENAME_WILDCARDS.iteritems():
                    if fnmatch.fnmatch(filename, wildcard):
                        self.assertFalse(match, filename)
                        match = True
                        formats_found.add(file_format)
                        yield os.path.join(root, filename), file_format
                self.assertTrue(match, filename)
        self.assertSetEqual(formats_found, set(FileFormat.list_definitions()))

    def test_track_types(self):
        for enum in FileFormat.list_definitions():
            self.assertIn(enum, FILE_FORMAT_SUPPORTED_TRACK_TYPES)

    def test_file_extensions(self):
        formats_from_wc = set(FILE_FORMAT_FILENAME_WILDCARDS.values())
        for enum in FileFormat.list_definitions():
            self.assertIn(enum, formats_from_wc)

    def test_samples_existence(self):
        found_formats = set()
        for _, file_format in self.list_samples():
            found_formats.add(file_format)
        self.assertSetEqual(found_formats, set(FileFormat.list_definitions()))

    def test_detectors(self):
        for detector in [FfmpegDetector(Ffmpeg()), MiDetector()]:
            for path, container_format in self.list_samples():
                if detector.is_container_format_supported(container_format):
                    detector.detect(path)  # TODO assert result
