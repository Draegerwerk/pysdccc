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


def test_download():
    """Test that the download function correctly downloads and extracts the executable."""
    url = httpx.URL(uuid.uuid4().hex)
    exe_path = pathlib.Path(uuid.uuid4().hex)
    with (
        mock.patch('pysdccc._download.open_download_stream'),
        mock.patch('zipfile.ZipFile'),
        mock.patch('pysdccc._common.get_exe_path') as mock_get_exe_path,
    ):
        mock_get_exe_path.return_value = exe_path
        assert download(url) == exe_path


@pytest.mark.asyncio
async def test_download_async():
    """Test that the download function correctly downloads and extracts the executable."""
    url = httpx.URL(uuid.uuid4().hex)
    exe_path = pathlib.Path(uuid.uuid4().hex)
    with (
        mock.patch('pysdccc._download.aopen_download_stream') as mock_response,
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


def test_is_downloaded():
    """Test that the download status is correctly determined."""
    assert not is_downloaded(uuid.uuid4().hex)
    with mock.patch('pysdccc._runner.SdcccRunner') as mock_runner:
        version = uuid.uuid4().hex
        mock_runner.return_value.get_version.return_value = version
        assert is_downloaded(version)


@pytest.mark.asyncio
async def test_is_downloaded_async():
    """Test that the download status is correctly determined."""
    assert not await ais_downloaded(uuid.uuid4().hex)
    with mock.patch('pysdccc._runner.SdcccRunnerAsync') as mock_runner:
        version = uuid.uuid4().hex

        async def _get_version():  # noqa: ANN202
            return version

        mock_runner.return_value.get_version = _get_version
        assert await ais_downloaded(version)
