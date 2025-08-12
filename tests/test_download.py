"""Provides functions for downloading and verifying the presence of the SDCcc executable."""

import pathlib
import uuid
from unittest import mock

import httpx
import pytest

from pysdccc._download import (
    adownload,
    ais_downloaded,
    download,
    is_downloaded,
)

pytestmark = pytest.mark.anyio


@mock.patch('pysdccc._download.adownload')
def test_download(mock_adownload: mock.AsyncMock):
    """Test that the download function correctly downloads and extracts the executable."""
    url = uuid.uuid4().hex
    exe_path = pathlib.Path(uuid.uuid4().hex)
    mock_adownload.return_value = exe_path
    assert download(url).result() == exe_path
    mock_adownload.assert_called_once_with(url, None, None)


async def test_download_async():
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
        assert await adownload(url) == exe_path


@mock.patch('pysdccc._download.ais_downloaded', return_value=True)
def test_is_downloaded(mock_ais_downloaded: mock.AsyncMock):
    """Test that the download status is correctly determined."""
    version = uuid.uuid4().hex
    assert is_downloaded(version)
    mock_ais_downloaded.assert_called_once_with(version)


async def test_is_downloaded_async():
    """Test that the download status is correctly determined."""
    assert not await ais_downloaded(uuid.uuid4().hex)
    with mock.patch('pysdccc._async_runner.SdcccRunnerAsync') as mock_runner:
        version = uuid.uuid4().hex
        mock_runner.return_value.get_version = mock.AsyncMock(return_value=version)
        assert await ais_downloaded(version)
