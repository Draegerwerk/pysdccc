"""Implements the runner for the SDCcc checker tool executable."""

import logging
import pathlib
from collections.abc import Sequence

import anyio

from pysdccc import _common
from pysdccc._common import _drain_stream

__LOGGER__ = logging.getLogger('pysdccc.checker_tool')


class SdcccCheckerTool:
    """Asynchronous runner for the SDCcc checker tool.

    The checker tool checks a single MdibVersion of an MDIB from a single SequenceId against a reference file,
    or generates a matching reference file based on such a provided MDIB.
    """

    def __init__(self, exe: _common.PATH_TYPE | None = None):
        """Initialize the SdcccCheckerTool object.

        :param exe: The path to the SDCcc checker tool executable. Must be an absolute path. Defaults to the checker
        tool of the downloaded SDCcc version.
        :raises ValueError: If the provided path is not absolute.
        :raises FileNotFoundError: If no executable is found under the provided or default path.
        """
        try:
            self._exe = (
                pathlib.Path(exe)
                if exe is not None
                else pathlib.Path(_common.get_checker_tool_exe_path(_common.DEFAULT_STORAGE_DIRECTORY)).absolute()
            )
        except FileNotFoundError as e:
            msg = 'Have you downloaded SDCcc?'
            raise FileNotFoundError(msg) from e
        if not self._exe.is_absolute():
            msg = f'Path to executable must be absolute but is {self._exe}'
            raise ValueError(msg)
        if not self._exe.is_file():
            msg = f'No executable found under {self._exe}'
            raise FileNotFoundError(msg)

    @property
    def exe(self) -> anyio.Path:
        """Get the path to the SDCcc checker tool executable."""
        return anyio.Path(self._exe)

    @staticmethod
    def _prepare_command(
        *args: str,
        mdib_path: anyio.Path,
        refpath: anyio.Path,
        **kwargs: _common.CMD_TYPE,
    ) -> Sequence[str]:
        if not mdib_path.is_absolute():
            msg = 'Path to mdib file must be absolute'
            raise ValueError(msg)
        if not refpath.is_absolute():
            msg = 'Path to reference file must be absolute'
            raise ValueError(msg)

        kwargs['mdibpath'] = mdib_path
        kwargs['refpath'] = refpath
        return _common.build_command(*args, **kwargs)

    async def run(
        self,
        *,
        mdib: _common.PATH_TYPE,
        reference: _common.PATH_TYPE,
        **kwargs: _common.CMD_TYPE,
    ) -> int:
        """Compare the given MDIB against the given reference file, or generate the reference file from the MDIB.

        :param mdib: The path to the MDIB xml file. Must be an absolute path.
        :param reference: The path to the reference json file. Must be an absolute path.
        :param kwargs: Additional command line arguments to be passed to the SDCcc checker tool executable.
        :return: The returncode of the checker tool process.
        :raises ValueError: If the provided paths are not absolute.
        """
        command = self._prepare_command(
            str(self.exe),
            mdib_path=anyio.Path(mdib),
            refpath=anyio.Path(reference),
            **kwargs,
        )

        async with await anyio.open_process(command, cwd=str(self.exe.parent)) as process:
            async with anyio.create_task_group() as tg:
                if process.stdout:
                    tg.start_soon(_drain_stream, process.stdout, __LOGGER__.info)

                if process.stderr:
                    tg.start_soon(_drain_stream, process.stderr, __LOGGER__.error)

            return await process.wait()

    async def get_version(self) -> str:
        """Get the version of the SDCcc checker tool executable."""
        result = await anyio.run_process([self.exe, '--version'], check=True, cwd=self.exe.parent)
        return result.stdout.decode(_common.ENCODING).strip()
