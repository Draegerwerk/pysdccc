"""Everything needed for downloading SDCcc."""

import concurrent.futures
import contextlib
import logging
import pathlib
import subprocess
import zipfile
from collections.abc import AsyncGenerator

import anyio.from_thread
import httpx

from pysdccc import _async_runner, _common

logger = logging.getLogger('pysdccc.download')


@contextlib.asynccontextmanager
async def _open_download_stream(
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
    async with (
        anyio.NamedTemporaryFile('wb', suffix='.zip', delete=False) as temporary_file,
        _open_download_stream(url, proxy=proxy) as response,
    ):
        async for chunk in response.aiter_bytes():
            await temporary_file.write(chunk)
    output = output or _common.DEFAULT_STORAGE_DIRECTORY
    logger.info('Extracting SDCcc to %s.', output)
    with zipfile.ZipFile(temporary_file.name) as f:  # pyright: ignore [reportCallIssue, reportArgumentType]
        f.extractall(output)
    return _common.get_exe_path(output)


async def ais_downloaded(version: str) -> bool:
    """Check if the SDCcc version is already downloaded.

    This function checks if the SDCcc executable is already downloaded.

    :return: True if the executable is already downloaded, False otherwise.
    """
    try:
        return await _async_runner.SdcccRunnerAsync(pathlib.Path().absolute()).get_version() == version
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def download(
    url: httpx.URL | str,
    proxy: httpx.Proxy | None = None,
    output: pathlib.Path | None = None,
) -> concurrent.futures.Future[pathlib.Path]:
    """Download and extract the specified version from the URL.

    :param url: The parsed URL from which to download the executable.
    :param proxy: Optional proxy to be used for the download.
    :param output: The path to the directory where the downloaded executable will be extracted. If None,
    `DEFAULT_STORAGE_DIRECTORY` is used.
    :return: Path to the executable.
    """
    with anyio.from_thread.start_blocking_portal() as portal:
        return portal.start_task_soon(adownload, url, proxy, output)


def is_downloaded(version: str) -> concurrent.futures.Future[bool]:
    """Check if the SDCcc version is already downloaded.

    This function checks if the SDCcc executable is already downloaded.

    :return: True if the executable is already downloaded, False otherwise.
    """
    with anyio.from_thread.start_blocking_portal() as portal:
        return portal.start_task_soon(ais_downloaded, version)
