"""tests for the _cli module."""

import pathlib
import random
import subprocess
import sys
import uuid
import zipfile
from unittest import mock

import click
import httpx
import pytest
from click.testing import CliRunner

import pysdccc
from pysdccc._cli import PROXY, URL, _download_to_stream, cli, download, sdccc


def test_url_type_success():
    """Test the URL type."""
    expected_url = httpx.URL('https://example.com')
    actual_url = URL.convert(str(expected_url), None, None)
    assert actual_url == expected_url


def test_url_type_failure():
    """Test the URL type with an invalid URL."""
    message = uuid.uuid4().hex
    url = uuid.uuid4().hex
    with mock.patch('httpx.URL', side_effect=Exception(message)), mock.patch('pysdccc._cli.URL.fail') as mock_fail:
        URL.convert(url, None, None)
        mock_fail.assert_called_once_with(f'{url} is not a valid url: {message}', None, None)


def test_proxy_type_success():
    """Test the proxy type."""
    for scheme in ('http', 'https', 'socks5', 'socks5h'):
        port = random.randint(0, 65535)
        url = uuid.uuid4().hex
        expected_proxy = httpx.Proxy(f'{scheme}://{url}:{port}')
        actual_proxy = PROXY.convert(str(expected_proxy.url), None, None)
        assert actual_proxy.url == expected_proxy.url


def test_proxy_type_failure():
    """Test the proxy type with an invalid proxy."""
    proxy = uuid.uuid4().hex
    with pytest.raises(click.BadParameter):
        PROXY.convert(proxy, None, None)


def test_download_to_stream_success(tmp_path: pathlib.Path):
    """Test _download_to_stream downloads data and writes to stream."""
    url = httpx.URL('https://example.com/file.zip')
    data = [b'abc', b'def', b'ghi']
    proxy = httpx.Proxy('http://proxy:8080')

    httpx_response = mock.MagicMock()
    httpx_response.headers = {'Content-Length': str(sum(len(chunk) for chunk in data))}
    httpx_response.num_bytes_downloaded = 0
    httpx_response.raise_for_status.return_value = None

    def iter_bytes():
        for chunk in data:
            httpx_response.num_bytes_downloaded += len(chunk)
            yield chunk

    httpx_response.iter_bytes.side_effect = iter_bytes
    httpx_response.__enter__.return_value = httpx_response
    httpx_response.__exit__.return_value = None

    with mock.patch('httpx.stream', return_value=httpx_response) as mock_stream:
        out_bin = tmp_path.joinpath('out.bin')
        with out_bin.open('wb') as stream:
            _download_to_stream(url, stream, proxy)
        assert out_bin.read_bytes() == b''.join(data)
    mock_stream.assert_called_once_with('GET', url, follow_redirects=True, proxy=proxy)


def test_download_to_stream_error():
    """Test _download_to_stream raises for HTTP error."""
    error_message = uuid.uuid4().hex
    url = httpx.URL('https://example.com/file.zip')
    proxy = httpx.Proxy('http://proxy:8080')
    httpx_response = mock.MagicMock()
    httpx_response.__enter__.return_value = httpx_response

    def raise_for_status():
        raise httpx.HTTPStatusError(error_message, request=mock.MagicMock(), response=mock.MagicMock())

    httpx_response.raise_for_status = raise_for_status
    with (
        mock.patch('httpx.stream', return_value=httpx_response) as mock_stream,
        pytest.raises(httpx.HTTPStatusError, match=error_message),
    ):
        _download_to_stream(url, mock.MagicMock(), proxy)
    mock_stream.assert_called_once_with('GET', url, follow_redirects=True, proxy=proxy)


def test_download_extracts_zip(tmp_path: pathlib.Path):
    """Test download extracts zip contents to output directory."""
    url = httpx.URL('https://example.com/file.zip')
    proxy = httpx.Proxy('http://proxy:8080')
    downloaded_zip_file = tmp_path / 'this_file_has_been_downloaded.zip'
    output_dir = tmp_path / 'output'
    output_dir.mkdir()

    # create a zip file which acts as it is the downloaded content
    archive_name = uuid.uuid4().hex
    downloaded_zip_file_content = uuid.uuid4().hex
    with zipfile.ZipFile(downloaded_zip_file, 'w') as zf:
        zf.writestr(archive_name, downloaded_zip_file_content)

    with (
        mock.patch('tempfile.NamedTemporaryFile') as mock_tempfile,
        mock.patch('pysdccc._cli._download_to_stream') as mock_download_to_stream,
    ):
        mock_tempfile.return_value.__enter__.return_value.name = str(downloaded_zip_file)
        download(url, output_dir, proxy)
    mock_download_to_stream.assert_called_once_with(url, mock_tempfile.return_value.__enter__(), proxy=proxy)

    output_file = output_dir / archive_name
    assert output_file.read_text() == downloaded_zip_file_content


def test_install_success():
    """Test the installation command."""
    runner = CliRunner()
    url = 'https://example.com/file.zip'
    with mock.patch('pysdccc._cli.uninstall') as mock_uninstall, mock.patch('pysdccc._cli.download') as mock_download:
        result = runner.invoke(cli, ['install', url])
    mock_uninstall.assert_called_once()
    mock_download.assert_called_once_with(url, pysdccc.DEFAULT_STORAGE_DIRECTORY, None)
    assert result.exit_code == 0


def test_install_failure():
    """Test the installation command for an error during download."""
    runner = CliRunner()
    url = 'https://example.com/file.zip'
    error_message = uuid.uuid4().hex

    def side_effect(*_, **__):  # noqa: ANN002, ANN003
        raise Exception(error_message)  # noqa: TRY002

    with mock.patch('pysdccc._cli.uninstall'), mock.patch('pysdccc._cli.download', side_effect=side_effect):
        result = runner.invoke(cli, ['install', url])
    assert result.exit_code == 1
    assert result.output == f'Error: Failed to download and extract SDCcc from {url}: {error_message}\n'


def test_uninstall(tmp_path: pathlib.Path):
    """Test the uninstallation command."""
    runner = CliRunner()
    assert tmp_path.exists()
    with mock.patch('pysdccc._cli._common.DEFAULT_STORAGE_DIRECTORY', tmp_path):
        result = runner.invoke(cli, ['uninstall'])
    assert result.exit_code == 0
    assert not tmp_path.exists()
    # if called again check that it does not fail even if the directory does not exist
    with mock.patch('pysdccc._cli._common.DEFAULT_STORAGE_DIRECTORY', tmp_path):
        result = runner.invoke(cli, ['uninstall'])
    assert result.exit_code == 0


def test_sdccc_success(tmp_path: pathlib.Path):
    """Test sdccc runs the executable successfully."""
    exe_path = tmp_path.joinpath(f'{uuid.uuid4().hex}.exe')
    with (
        mock.patch('pysdccc._common.get_exe_path', return_value=exe_path),
        mock.patch('subprocess.run') as mock_run,
        mock.patch('sys.argv', [exe_path, '--foo', uuid.uuid4().hex]) as mock_sys_argv,
    ):
        sdccc()
    mock_run.assert_called_once_with(mock_sys_argv, check=True, cwd=exe_path.parent)


def test_sdccc_file_not_found(tmp_path: pathlib.Path):
    """Test sdccc when executable is not found."""
    exe_path = tmp_path.joinpath(f'{uuid.uuid4().hex}.exe')

    def side_effect(*_, **__):  # noqa: ANN002, ANN003
        msg = f'Executable not found at {exe_path}'
        raise FileNotFoundError(msg)

    with (
        mock.patch('pysdccc._common.get_exe_path', return_value=exe_path),
        mock.patch('subprocess.run', side_effect=side_effect) as mock_run,
        pytest.raises(SystemExit) as excinfo,
    ):
        sdccc()
    mock_run.assert_called_once_with([exe_path, *sys.argv[1:]], check=True, cwd=exe_path.parent)
    assert excinfo.value.code == 1


def test_sdccc_subprocess_error():
    """Test sdccc when subprocess.run returns non-zero exit code."""
    exe_path = pathlib.Path(f'/fake/path/{uuid.uuid4().hex}.exe')

    return_code = random.randint(1, 100)

    def side_effect(*_, **__):  # noqa: ANN002, ANN003
        raise subprocess.CalledProcessError(returncode=return_code, cmd=mock.MagicMock())

    with (
        mock.patch('pysdccc._common.get_exe_path', return_value=exe_path),
        mock.patch('subprocess.run', side_effect=side_effect),
        pytest.raises(SystemExit) as excinfo,
    ):
        sdccc()
    assert excinfo.value.code == return_code
