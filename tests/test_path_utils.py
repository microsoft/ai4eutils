"""
Unit tests for path_utils.py

From the ai4eutils folder, run:
    # run all tests, -v for verbose output
    python -m unittest -v tests/test_path_utils.py

    # run a specific test
    python -m unittest -v tests.test_path_utils.Tests.test_split_path
"""
from datetime import datetime
import unittest
from unittest import mock

from path_utils import (
    fileparts,
    insert_before_extension,
    split_path,
    top_level_folder)


class Tests(unittest.TestCase):
    """Tests for path_utils.py"""

    def test_split_path(self):
        # Windows paths
        test_paths = {
            r'c:\dir\subdir\file.jpg': ['c:\\', 'dir', 'subdir', 'file.jpg'],
            r'c:\dir\subdir\file': ['c:\\', 'dir', 'subdir', 'file'],
            r'c:\dir\file.jpg': ['c:\\', 'dir', 'file.jpg'],
            r'c:\dir\file': ['c:\\', 'dir', 'file'],
            r'c:\file.jpg': ['c:\\', 'file.jpg'],
            r'c:\file': ['c:\\', 'file'],
            r'..\subdir\file.jpg': ['..', 'subdir', 'file.jpg'],
            r'..\subdir\file': ['..', 'subdir', 'file'],
            r'..\file.jpg': ['..', 'file.jpg'],
            r'..\file': ['..', 'file'],
            r'file.jpg': ['file.jpg'],
            r'file': ['file'],
        }
        for path, result in test_paths.items():
            self.assertEqual(split_path(path), result)

        # Unix paths
        test_paths = {
            '/dir/subdir/file.jpg': ['/', 'dir', 'subdir', 'file.jpg'],
            '/dir/subdir/file': ['/', 'dir', 'subdir', 'file'],
            '/dir/file.jpg': ['/', 'dir', 'file.jpg'],
            '/dir/file': ['/', 'dir', 'file'],
            'file.jpg': ['file.jpg'],
            'file': ['file'],
            '../subdir/file.jpg': ['..', 'subdir', 'file.jpg'],
            '../subdir/file': ['..', 'subdir', 'file'],
            '../file.jpg': ['..', 'file.jpg'],
            '../file': ['..', 'file'],
        }
        for path, result in test_paths.items():
            self.assertEqual(split_path(path), result)

    def test_fileparts(self):
        # Windows paths
        test_paths = {
            r'c:\dir\subdir\file.jpg': (r'c:\dir\subdir', 'file', '.jpg'),
            r'c:\dir\subdir\file': (r'c:\dir\subdir', 'file', ''),
            r'c:\dir\file.jpg': (r'c:\dir', 'file', '.jpg'),
            r'c:\dir\file': (r'c:\dir', 'file', ''),
            r'c:\file.jpg': ('c:\\', 'file', '.jpg'),
            r'c:\file': ('c:\\', 'file', ''),
            r'..\subdir\file.jpg': (r'..\subdir', 'file', '.jpg'),
            r'..\subdir\file': (r'..\subdir', 'file', ''),
            r'..\file.jpg': ('..', 'file', '.jpg'),
            r'..\file': ('..', 'file', ''),
            r'file.jpg': ('', 'file', '.jpg'),
            r'file': ('', 'file', ''),
        }
        for path, result in test_paths.items():
            self.assertEqual(fileparts(path), result)

        # Unix paths
        test_paths = {
            '/dir/subdir/file.jpg': ('/dir/subdir', 'file', '.jpg'),
            '/dir/subdir/file': ('/dir/subdir', 'file', ''),
            '/dir/file.jpg': ('/dir', 'file', '.jpg'),
            '/dir/file': ('/dir', 'file', ''),
            'file.jpg': ('', 'file', '.jpg'),
            'file': ('', 'file', ''),
            '../subdir/file.jpg': ('../subdir', 'file', '.jpg'),
            '../subdir/file': ('../subdir', 'file', ''),
            '../file.jpg': ('..', 'file', '.jpg'),
            '../file': ('..', 'file', ''),
        }
        for path, result in test_paths.items():
            self.assertEqual(fileparts(path), result)

    @mock.patch('path_utils.datetime')
    def test_insert_before_extension(self, mock_dt):
        # Unix path with extension
        r = insert_before_extension(
            filename='/dir/subdir/file.jpg',
            s='newstring')
        self.assertEqual(r, '/dir/subdir/file.newstring.jpg')

        # Windows path with extension
        r = insert_before_extension(
            filename=r'c:\dir\file.jpg',
            s='newstring')
        self.assertEqual(r, r'c:\dir\file.newstring.jpg')

        # Unix path without extension
        r = insert_before_extension(
            filename='/dir/subdir/file',
            s='newstring')
        self.assertEqual(r, '/dir/subdir/file.newstring')

        # Windows path without extension
        r = insert_before_extension(
            filename=r'c:\dir\file',
            s='newstring')
        self.assertEqual(r, r'c:\dir\file.newstring')

        # Unix path without extra string (i.e., use timestamp)
        mock_dt.now = mock.Mock(return_value=datetime(2020, 7, 15, 10, 13, 46))
        timestamp = '2020.07.15.10.13.46'
        r = insert_before_extension(filename='/dir/subdir/file.jpg')
        self.assertEqual(r, f'/dir/subdir/file.{timestamp}.jpg')

    def test_top_level_folder(self):
        # Unix paths
        test_paths = {
            'blah/foo/bar': 'blah',
            '/blah/foo/bar': '/blah',
            'bar': 'bar',
            '': '',
        }
        for path, result in test_paths.items():
            self.assertEqual(top_level_folder(path, windows=False), result)

        # Windows paths
        test_paths = {
            '': '',
            'c:\\': 'c:\\',
            r'c:\blah': r'c:\blah',
            r'c:\foo': r'c:\foo',
            r'c:/foo': 'c:/foo',
            r'c:\foo/bar': r'c:\foo'
        }
        for path, result in test_paths.items():
            self.assertEqual(top_level_folder(path, windows=True), result)


if __name__ == '__main__':
    unittest.main()
