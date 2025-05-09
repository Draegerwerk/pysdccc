"""Command line interface."""

import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile
import zipfile

import httpx

from pysdccc import _common, _download

try:
    import click
except ImportError as import_error:
    msg = 'Cli not installed. Please install "pysdccc[cli]" package.'
    raise ImportError(msg) from import_error


class UrlType(click.ParamType):
    """Url type."""

    name = 'url'

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> httpx.URL:
        """Convert value to url."""
        try:
            return httpx.URL(value)
        except Exception as e:  # noqa: BLE001
            self.fail(f'{value!r} is not a valid url: {e}', param, ctx)


URL = UrlType()


class ProxyType(click.ParamType):
    """Proxy type."""

    name = 'proxy'

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> httpx.Proxy | None:
        """Convert value to proxy."""
        try:
            return httpx.Proxy(value)
        except Exception as e:  # noqa: BLE001
            self.fail(f'{value!r} is not a valid proxy: {e}', param, ctx)


PROXY = ProxyType()


def _download_to_stream(url: httpx.URL, stream: io.IOBase, proxy: httpx.Proxy | None = None) -> None:
    with _download.open_download_stream(url, proxy) as response:
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


def download(url: httpx.URL, output: pathlib.Path, proxy: httpx.Proxy | None = None):
    """Download and extract the executable from an url."""
    click.echo(f'Downloading SDCcc from {url}.')
    with tempfile.NamedTemporaryFile('wb', suffix='.zip', delete=False) as temporary_file:
        _download_to_stream(url, temporary_file, proxy=proxy)  # type: ignore[arg-type]
    click.echo(f'Extracting SDCcc to {output}.')
    with (
        zipfile.ZipFile(temporary_file.name) as f,
        click.progressbar(f.infolist(), label='Extracting', width=0) as progress,
    ):
        for member in progress:
            f.extract(member, output)


@click.group(help='Manage SDCcc installation.')
@click.version_option(message='%(version)s')
def cli():
    pass


@click.command(
    short_help='Install the SDCcc executable from the specified URL. Releases can be found at https://github.com/Draegerwerk/SDCcc/releases.',
)
@click.argument('url', type=URL)
@click.option('--proxy', help='Proxy server to use for the download.', type=PROXY)
@click.pass_context
def install(ctx: click.Context, url: httpx.URL, proxy: httpx.Proxy | None):
    """Download the specified version from the default URL to a temporary directory.

    This function downloads the SDCcc executable from the given URL to a temporary directory.
    It optionally uses a proxy and a specified timeout for the download operation.
    The downloaded file is extracted to a local path determined by the version string in the URL.

    :param ctx: context from click
    :param url: The parsed URL from which to download the executable.
    :param proxy: Optional proxy to be used for the download.
    """
    ctx.invoke(uninstall)
    try:
        download(url, _common.DEFAULT_STORAGE_DIRECTORY, proxy)
    except Exception as e:
        msg = f'Failed to download and extract SDCcc from {url}: {e}.'
        raise click.ClickException(msg) from e


@click.command(short_help='Uninstall the SDCcc executable by removing the directory.')
def uninstall():
    """Uninstall the SDCcc executable.

    This function removes the SDCcc executable from the directory.
    """
    import shutil

    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(_common.DEFAULT_STORAGE_DIRECTORY)


cli.add_command(install)
cli.add_command(uninstall)


def sdccc():
    try:
        sdccc_exe = _common.get_exe_path(_common.DEFAULT_STORAGE_DIRECTORY)
        subprocess.run(  # noqa: S603
            [sdccc_exe, *sys.argv[1:]],
            check=True,
            cwd=sdccc_exe.parent,
        )
    except FileNotFoundError as e:
        click.ClickException("SDCcc is not installed. Please install using 'pysdccc install <url>'.").show()
        raise SystemExit(1) from e
    except subprocess.CalledProcessError as e:
        click.echo(e, err=True)
        raise SystemExit(e.returncode) from e
