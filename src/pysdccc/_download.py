"""Everything needed for downloading SDCcc."""

import concurrent.futures
import contextlib
import logging
import os
import subprocess
import sys
import zipfile
from collections.abc import AsyncGenerator
from typing import cast

import anyio.from_thread
import anyio.to_thread
import httpx

from pysdccc import _common, _runner

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

logger = logging.getLogger('pysdccc.download')


def _extract_zip_file_sync(zip_file_path: _common.PATH_TYPE, output: _common.PATH_TYPE) -> None:
    """Extract the given zip file to the given output directory."""
    with zipfile.ZipFile(zip_file_path) as f:
        f.extractall(output)


async def extract_zip_file(zip_file_path: _common.PATH_TYPE, output: _common.PATH_TYPE) -> None:
    """Extract the given zip file to the given output directory.

    :param zip_file_path: The path to the zip file to be extracted.
    :param output: The path to the directory where the zip file will be extracted.
    """
    logger.info('Extracting SDCcc to %s.', output)
    await anyio.to_thread.run_sync(_extract_zip_file_sync, zip_file_path, output)


@contextlib.asynccontextmanager
async def _open_download_stream(
    url: httpx.URL,
    proxy: httpx.Proxy | None = None,
) -> AsyncGenerator[httpx.Response, None]:
    """Open a stream from which SDCcc can be downloaded chunk by chunk."""
    async with httpx.AsyncClient(follow_redirects=True, proxy=proxy) as client, client.stream('GET', url) as response:
        response.raise_for_status()
        yield response


async def download(
    url: httpx.URL | str,
    proxy: httpx.Proxy | None = None,
    output: _common.PATH_TYPE | None = None,
) -> os.PathLike[str]:
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
        temporary_file_path = anyio.Path(cast('str', temporary_file.name))
        async for chunk in response.aiter_bytes():
            await temporary_file.write(chunk)
    output = output or _common.DEFAULT_STORAGE_DIRECTORY
    try:
        logger.info('Extracting SDCcc to %s.', output)
        await extract_zip_file(temporary_file_path, output)
    finally:
        with contextlib.suppress(OSError):
            await temporary_file_path.unlink()
    return _common.get_exe_path(output)


async def is_downloaded(version: str) -> bool:
    """Check if the SDCcc version is already downloaded.

    This function checks if the SDCcc executable is already downloaded.

    :return: True if the executable is already downloaded, False otherwise.
    """
    try:
        return await _runner.SdcccRunner(await anyio.Path().absolute()).get_version() == version
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


async def install(path: _common.PATH_TYPE, output: _common.PATH_TYPE | None = None) -> None:
    """Install the SDCcc executable from the given remote or local path.

    This function installs the SDCcc executable from the given path. It checks if the path is a URL or a local file
    path and calls the appropriate function to download and extract the zip file.

    :param path: The remote or local path to the SDCcc executable.
    :param output: The path to the directory where the downloaded executable will be extracted. If None,
    `DEFAULT_STORAGE_DIRECTORY` is used.
    """
    if _common.is_remote_path(path):
        await download(str(path), output=output or _common.DEFAULT_STORAGE_DIRECTORY)
    else:
        await extract_zip_file(path, output or _common.DEFAULT_STORAGE_DIRECTORY)


@deprecated('Prefer using the async version `download` instead.')
def download_sync(
    url: httpx.URL | str,
    proxy: httpx.Proxy | None = None,
    output: _common.PATH_TYPE | None = None,
) -> concurrent.futures.Future[os.PathLike[str]]:
    """Download and extract the specified version from the URL.

    :param url: The parsed URL from which to download the executable.
    :param proxy: Optional proxy to be used for the download.
    :param output: The path to the directory where the downloaded executable will be extracted. If None,
    `DEFAULT_STORAGE_DIRECTORY` is used.
    :return: Path to the executable.
    """
    with anyio.from_thread.start_blocking_portal() as portal:
        return portal.start_task_soon(download, url, proxy, output)


@deprecated('Prefer using the async version `is_downloaded` instead.')
def is_downloaded_sync(version: str) -> concurrent.futures.Future[bool]:
    """Check if the SDCcc version is already downloaded.

    This function checks if the SDCcc executable is already downloaded.

    :return: True if the executable is already downloaded, False otherwise.
    """
    with anyio.from_thread.start_blocking_portal() as portal:
        return portal.start_task_soon(is_downloaded, version)
