"""Everything needed for downloading SDCcc."""

import contextlib
import logging
import pathlib
import subprocess
import tempfile
import zipfile
from collections.abc import AsyncGenerator, Generator

import httpx

from pysdccc import _common, _runner

logger = logging.getLogger('pysdccc.download')


@contextlib.contextmanager
def open_download_stream(
    url: httpx.URL, proxy: httpx.Proxy | None = None, timeout: float | None = None
) -> Generator[httpx.Response, None, None]:
    """Open a stream from which SDCcc can be downloaded chunk by chunk."""
    with httpx.stream('GET', url, follow_redirects=True, proxy=proxy, timeout=timeout) as response:
        response.raise_for_status()
        yield response


def download(
    url: httpx.URL | str,
    proxy: httpx.Proxy | None = None,
    output: pathlib.Path | None = None,
    timeout: float | None = None,
) -> pathlib.Path:
    """Download and extract the specified version from the URL.

    :param url: The parsed URL from which to download the executable.
    :param proxy: Optional proxy to be used for the download.
    :param output: The path to the directory where the downloaded executable will be extracted. If None,
    `DEFAULT_STORAGE_DIRECTORY` is used.
    :param timeout: Optional timeout in seconds for the download.
    :return: Path to the executable.
    """
    url = httpx.URL(url)
    logger.info('Downloading SDCcc from %s.', url)
    with (
        tempfile.NamedTemporaryFile('wb', suffix='.zip', delete=False) as temporary_file,
        open_download_stream(url, proxy, timeout) as response,
    ):
        for chunk in response.iter_bytes():
            temporary_file.write(chunk)
    output = output or _common.DEFAULT_STORAGE_DIRECTORY
    logger.info('Extracting SDCcc to %s.', output)
    with zipfile.ZipFile(temporary_file.name) as f:
        f.extractall(output)
    return _common.get_exe_path(output)


def is_downloaded(version: str) -> bool:
    """Check if the SDCcc version is already downloaded.

    This function checks if the SDCcc executable is already downloaded.

    :return: True if the executable is already downloaded, False otherwise.
    """
    try:
        return _runner.SdcccRunner(pathlib.Path().absolute()).get_version() == version
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


@contextlib.asynccontextmanager
async def aopen_download_stream(
    url: httpx.URL,
    proxy: httpx.Proxy | None = None,
) -> AsyncGenerator[httpx.Response, None]:
    """Open a stream from which SDCcc can be downloaded chunk by chunk."""
    client = httpx.AsyncClient(follow_redirects=True, proxy=proxy)
    async with client.stream('GET', url) as response:
        response.raise_for_status()
        yield response


async def adownload(
    url: httpx.URL | str,
    proxy: httpx.Proxy | None = None,
    output: pathlib.Path | None = None,
) -> pathlib.Path:
    """Download and extract the specified version from the URL.

    :param url: The parsed URL from which to download the executable.
    :param proxy: Optional proxy to be used for the download.
    :param output: The path to the directory where the downloaded executable will be extracted. If None,
    `DEFAULT_STORAGE_DIRECTORY` is used.
    :return: Path to the executable.
    """
    url = httpx.URL(url)
    logger.info('Downloading SDCcc from %s.', url)
    with tempfile.NamedTemporaryFile('wb', suffix='.zip', delete=False) as temporary_file:
        async with aopen_download_stream(url, proxy=proxy) as response:
            async for chunk in response.aiter_bytes():
                temporary_file.write(chunk)
    output = output or _common.DEFAULT_STORAGE_DIRECTORY
    logger.info('Extracting SDCcc to %s.', output)
    with zipfile.ZipFile(temporary_file.name) as f:
        f.extractall(output)
    return _common.get_exe_path(output)


async def ais_downloaded(version: str) -> bool:
    """Check if the SDCcc version is already downloaded.

    This function checks if the SDCcc executable is already downloaded.

    :return: True if the executable is already downloaded, False otherwise.
    """
    try:
        return await _runner.SdcccRunnerAsync(pathlib.Path().absolute()).get_version() == version
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
