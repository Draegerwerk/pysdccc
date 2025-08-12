"""Python wrapper to the SDCcc tool for testing SDC devices."""

from pysdccc._async_runner import SdcccRunnerAsync
from pysdccc._common import DEFAULT_STORAGE_DIRECTORY, check_requirements
from pysdccc._download import adownload, ais_downloaded, download, is_downloaded
from pysdccc._result_parser import TestCase, TestSuite
from pysdccc._runner import (
    SdcccRunner,
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
