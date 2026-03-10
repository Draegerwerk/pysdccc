"""Command line interface."""

import contextlib
import io
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

import httpx

from pysdccc import _common

try:
    import click
except ImportError as import_error:
    raise ImportError('Cli not installed. Please install "pysdccc[cli]" package.') from import_error  # noqa: EM101, TRY003


class LocalOrRemotePath(click.ParamType):
    """Local or remote path type."""

    name = 'path'

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> httpx.URL | pathlib.Path:
        """Convert value to url or filepath."""
        if _common.is_remote_path(value):
            try:
                return httpx.URL(value)
            except Exception as e:  # noqa: BLE001
                self.fail(f'{value} is not a valid url: {e}', param, ctx)
        else:
            path = pathlib.Path(value)
            if not path.is_file():
                self.fail(f'{value} is not a valid file path.', param, ctx)
            return path


PATH = LocalOrRemotePath()


class ProxyType(click.ParamType):
    """Proxy type."""

    name = 'proxy'

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> httpx.Proxy:
        """Convert value to proxy."""
        try:
            return httpx.Proxy(value)
        except Exception as e:  # noqa: BLE001
            self.fail(f'{value} is not a valid proxy: {e}', param, ctx)


PROXY = ProxyType()


def _download_to_stream(url: httpx.URL, stream: io.IOBase, proxy: httpx.Proxy | None = None) -> None:
    with httpx.stream('GET', url, follow_redirects=True, proxy=proxy) as response:
        response.raise_for_status()
        total = response.headers.get('Content-Length')
        with click.progressbar(
            response.iter_bytes(),
            length=int(total) if total is not None else None,
            label='Downloading',
            show_eta=True,
            width=0,
        ) as progress:
            num_bytes_downloaded = response.num_bytes_downloaded
            for chunk in progress:
                stream.write(chunk)
                progress.update(response.num_bytes_downloaded - num_bytes_downloaded)
                num_bytes_downloaded = response.num_bytes_downloaded


def extract_zip_file(zip_file: _common.PATH_TYPE, output: _common.PATH_TYPE):
    click.echo(f'Extracting SDCcc to {output}.')
    with (
        zipfile.ZipFile(zip_file) as f,
        click.progressbar(f.infolist(), label='Extracting', width=0) as progress,
    ):
        for member in progress:
            f.extract(member, output)


def download(url: httpx.URL, stream: io.IOBase, proxy: httpx.Proxy | None = None):
    """Download the executable from a url to a given stream."""
    click.echo(f'Downloading SDCcc from {url}.')
    _download_to_stream(url, stream, proxy=proxy)


@click.group(help='Manage SDCcc installation.')
@click.version_option(message='%(version)s')
def cli():
    pass


@cli.command(
    short_help='Install the SDCcc executable from the specified local or remote path. Releases can be found at https://github.com/Draegerwerk/SDCcc/releases.',
)
@click.argument('path', type=PATH)
@click.option('--proxy', help='Proxy server to use for the download.', type=PROXY)
@click.pass_context
def install(ctx: click.Context, path: httpx.URL | pathlib.Path, proxy: httpx.Proxy | None):
    """Install the specified version from the local or remote path.

    :param ctx: context from click
    :param path: The URL from which to download the executable or a local path from which the file is extracted.
    :param proxy: Optional proxy to be used for the download.
    """
    ctx.invoke(uninstall)
    if isinstance(path, httpx.URL):
        try:
            with tempfile.NamedTemporaryFile('wb', suffix='.zip', delete=False) as stream:
                download(path, stream, proxy)  # ty:ignore[invalid-argument-type]
            file_to_be_extracted = stream.name
        except Exception as e:
            with contextlib.suppress(OSError):
                pathlib.Path(stream.name).unlink()
            msg = f'Failed to download SDCcc from {path}: {e}'
            raise click.ClickException(msg) from e
    elif isinstance(path, pathlib.Path):
        file_to_be_extracted = str(path)
    else:
        msg = f'Unexpected type of path: {type(path)}'
        raise TypeError(msg)

    try:
        extract_zip_file(file_to_be_extracted, _common.DEFAULT_STORAGE_DIRECTORY)
    except Exception as e:
        msg = f'Failed to extract SDCcc from {path}: {e}'
        raise click.ClickException(msg) from e
    finally:
        if isinstance(path, httpx.URL):
            with contextlib.suppress(OSError):
                pathlib.Path(file_to_be_extracted).unlink()


@cli.command(short_help='Uninstall the SDCcc executable by removing the directory.')
def uninstall():
    """Uninstall the SDCcc executable.

    This function removes the SDCcc executable from the directory.
    """
    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(_common.DEFAULT_STORAGE_DIRECTORY)


def sdccc():
    try:
        sdccc_exe = pathlib.Path(_common.get_exe_path(_common.DEFAULT_STORAGE_DIRECTORY))
        subprocess.run(  # noqa: S603
            [sdccc_exe, *sys.argv[1:]],
            check=True,
            cwd=sdccc_exe.parent,
        )
    except FileNotFoundError as e:
        # because this is not a click command, we need to handle the error manually
        click.echo("SDCcc is not installed. Please install using 'pysdccc install <url>'.", err=True)
        raise SystemExit(1) from e
    except subprocess.CalledProcessError as e:
        click.echo(e, err=True)
        raise SystemExit(e.returncode) from e
