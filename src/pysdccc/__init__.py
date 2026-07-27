"""Python wrapper to the SDCcc tool for testing SDC devices."""

from pysdccc._common import DEFAULT_STORAGE_DIRECTORY, check_requirements
from pysdccc._download import (
    download,
    download_sync,  # ty:ignore[deprecated]
    extract_zip_file,
    install,
    is_downloaded,
    is_downloaded_sync,  # ty:ignore[deprecated]
)
from pysdccc._result_parser import TestCase, TestSuite
from pysdccc._runner import (
    SdcccRunner,
    SdcccRunnerSync,  # ty:ignore[deprecated]
)

__all__ = [
    'DEFAULT_STORAGE_DIRECTORY',
    'SdcccRunner',
    'SdcccRunnerSync',
    'TestCase',
    'TestSuite',
    'check_requirements',
    'download',
    'download_sync',
    'extract_zip_file',
    'install',
    'is_downloaded',
    'is_downloaded_sync',
]
