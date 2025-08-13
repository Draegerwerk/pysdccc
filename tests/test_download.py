"""Provides functions for downloading and verifying the presence of the SDCcc executable."""

import pathlib
import uuid
from unittest import mock

import httpx
import pytest

from pysdccc._download import (
    download,
    download_sync,
    is_downloaded,
    is_downloaded_sync,
)

pytestmark = pytest.mark.anyio


@mock.patch('pysdccc._download.download')
def test_download_sync(mock_download: mock.AsyncMock):
    """Test that the download function correctly downloads and extracts the executable."""
    url = uuid.uuid4().hex
    exe_path = pathlib.Path(uuid.uuid4().hex)
    mock_download.return_value = exe_path
    assert download_sync(url).result() == exe_path
    mock_download.assert_called_once_with(url, None, None)


async def test_download():
    """Test that the download function correctly downloads and extracts the executable."""
    url = httpx.URL(uuid.uuid4().hex)
    exe_path = pathlib.Path(uuid.uuid4().hex)
    with (
        mock.patch('pysdccc._download._open_download_stream') as mock_response,
        mock.patch('zipfile.ZipFile'),
        mock.patch('pysdccc._common.get_exe_path') as mock_get_exe_path,
    ):
        response_mock = mock.AsyncMock()
        response_mock.aiter_bytes = mock.MagicMock()
        response_mock_context = mock.AsyncMock()
        response_mock_context.__aenter__.return_value = response_mock
        mock_response.return_value = response_mock_context
        mock_get_exe_path.return_value = exe_path
        assert await download(url) == exe_path


@mock.patch('pysdccc._download.is_downloaded', return_value=True)
def test_is_downloaded_sync(mock_is_downloaded: mock.AsyncMock):
    """Test that the download status is correctly determined."""
    version = uuid.uuid4().hex
    assert is_downloaded_sync(version).result()
    mock_is_downloaded.assert_called_once_with(version)


async def test_is_downloaded():
    """Test that the download status is correctly determined."""
    assert not await is_downloaded(uuid.uuid4().hex)
    with mock.patch('pysdccc._runner.SdcccRunner') as mock_runner:
        version = uuid.uuid4().hex
        mock_runner.return_value.get_version = mock.AsyncMock(return_value=version)
        assert await is_downloaded(version)
