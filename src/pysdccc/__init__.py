"""Python wrapper to the sdccc tool for testing SDC devices."""

from pysdccc._download import adownload, ais_downloaded, download, is_downloaded
from pysdccc._result_parser import TestCase, TestSuite
from pysdccc._runner import (
    DEFAULT_STORAGE_DIRECTORY,
    SdcccRunner,
    SdcccRunnerAsync,
    check_requirements,
)

__version__ = '0.0.0'

__all__ = [
    'DEFAULT_STORAGE_DIRECTORY',
    'SdcccRunner',
    'SdcccRunnerAsync',
    'TestCase',
    'TestSuite',
    'adownload',
    'ais_downloaded',
    'check_requirements',
    'download',
    'is_downloaded',
]
