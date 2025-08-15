"""Implements the runner for the SDCcc executable."""

import logging
import pathlib
import tomllib
import typing
from collections.abc import Callable

import anyio
from anyio.abc import ByteReceiveStream
from anyio.streams.text import TextReceiveStream

from pysdccc import _common
from pysdccc._result_parser import TestSuite

DIRECT_TEST_RESULT_FILE_NAME = 'TEST-SDCcc_direct.xml'
INVARIANT_TEST_RESULT_FILE_NAME = 'TEST-SDCcc_invariant.xml'


__LOGGER__ = logging.getLogger('pysdccc.run')


async def _drain_stream(stream: ByteReceiveStream, log: Callable[[object], None]) -> None:
    """Drain the given stream and log its content."""
    async for chunk in TextReceiveStream(stream, encoding=_common.ENCODING):
        log(chunk.strip())


class SdcccRunner:
    """Asynchronous runner for SDCcc."""

    def __init__(self, test_run_dir: _common.PATH_TYPE, exe: _common.PATH_TYPE | None = None):
        """Initialize the SdcccRunner object.

        :param exe: The path to the SDCcc executable. Must be an absolute path.
        :param test_run_dir: The path to the directory where the test run results are to be stored. Must be an absolute
        path.
        :raises ValueError: If the provided paths are not absolute.
        """
        try:
            self._exe = (
                pathlib.Path(exe)
                if exe is not None
                else pathlib.Path(_common.get_exe_path(_common.DEFAULT_STORAGE_DIRECTORY)).absolute()
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
        self._test_run_dir = pathlib.Path(test_run_dir)
        if not self._test_run_dir.is_absolute():
            msg = f'Path to test run directory must be absolute but is {self._test_run_dir}'
            raise ValueError(msg)
        if not self._test_run_dir.is_dir():
            msg = f'Test run directory "{self._test_run_dir}" is not a directory or does not exist'
            raise ValueError(msg)

    @property
    def exe(self) -> anyio.Path:
        """Get the path to the SDCcc executable."""
        return anyio.Path(self._exe)

    @property
    def test_run_dir(self) -> anyio.Path:
        """Get the path to the test run directory."""
        return anyio.Path(self._test_run_dir)

    async def get_config(self) -> dict[str, typing.Any]:
        """Get the default configuration.

        This method loads the default configuration from the SDCcc executable's directory.

        :return: A dictionary containing the configuration data.
        """
        return tomllib.loads(await self.exe.parent.joinpath('configuration').joinpath('config.toml').read_text())

    async def get_requirements(self) -> dict[str, dict[str, bool]]:
        """Get the default requirements.

        This method loads the default requirements from the SDCcc executable's directory.

        :return: A dictionary containing the requirements data.
        """
        return tomllib.loads(
            await self.exe.parent.joinpath('configuration').joinpath('test_configuration.toml').read_text()
        )

    async def get_test_parameter(self) -> dict[str, typing.Any]:
        """Get the default test parameter.

        This method loads the default test parameters from the SDCcc executable's directory.

        :return: A dictionary containing the test parameter data.
        """
        return tomllib.loads(
            await self.exe.parent.joinpath('configuration').joinpath('test_parameter.toml').read_text()
        )

    async def check_requirements(self, path: _common.PATH_TYPE) -> None:
        """Check the requirements from the given file against the requirements provided by the SDCcc version.

        This method verifies that all the requirements specified in the user's requirements file are supported by the
        requirements provided by the SDCcc version. If any requirement is not found, a KeyError is raised.

        :param path: The path to the user's requirements file.
        :raises KeyError: If a standard or requirement provided by the user is not found in the SDCcc provided
        requirements.
        """
        sdccc_provided_requirements = await self.get_requirements()
        user_provided_requirements = tomllib.loads(await anyio.Path(path).read_text())
        _common.check_requirements(user_provided_requirements, sdccc_provided_requirements)

    async def _get_result(self, file_name: str) -> TestSuite | None:
        """Get the parsed results of the test run.

        This method reads the direct and invariant test result files from the test run directory and returns them
        as TestSuite objects.

        :param file_name: The name of the result file to read.
        :return: A test suite containing the parsed results, or None if the file does not exist.
        """
        test_result_dir = self.test_run_dir.joinpath(file_name)
        if not await test_result_dir.exists():
            return None
        return await TestSuite.from_file(test_result_dir)

    async def _prepare_command(
        self,
        *args: str,
        config: anyio.Path,
        requirements: anyio.Path,
        **kwargs: _common.CMD_TYPE,
    ) -> list[str]:
        if not config.is_absolute():
            msg = 'Path to config file must be absolute'
            raise ValueError(msg)
        if not requirements.is_absolute():
            msg = 'Path to requirements file must be absolute'
            raise ValueError(msg)
        async for _ in self.test_run_dir.iterdir():
            msg = f'{self.test_run_dir} is not empty'
            raise ValueError(msg)

        kwargs['no_subdirectories'] = 'true'
        kwargs['test_run_directory'] = self.test_run_dir
        kwargs['config'] = config
        kwargs['testconfig'] = requirements
        return _common.build_command(*args, **kwargs)

    async def run(
        self,
        *,
        config: _common.PATH_TYPE,
        requirements: _common.PATH_TYPE,
        **kwargs: _common.CMD_TYPE,
    ) -> tuple[int, TestSuite | None, TestSuite | None]:
        """Run the SDCcc executable using the specified configuration and requirements.

        This method executes the SDCcc executable with the provided configuration and requirements files,
        and additional command line arguments. It logs the stdout and stderr of the process and waits for the
        process to complete or timeout.
        Checkout more parameter under https://github.com/draegerwerk/sdccc?tab=readme-ov-file#running-sdccc

        :param config: The path to the configuration file. Must be an absolute path.
        :param requirements: The path to the requirements file. Must be an absolute path.
        :param kwargs: Additional command line arguments to be passed to the SDCcc executable.
        :return: A tuple containing the returncode of the SDCcc process, parsed direct and invariant test results as
        TestSuite objects.
        :raises ValueError: If the provided paths are not absolute.
        """
        return_code = 1  # prevents possibly unbound variable
        command = await self._prepare_command(
            str(self.exe), config=anyio.Path(config), requirements=anyio.Path(requirements), **kwargs
        )

        async with (
            await anyio.open_process(command, cwd=str(self.exe.parent)) as process,
            anyio.create_task_group() as tg,
        ):
            if process.stdout:
                tg.start_soon(_drain_stream, process.stdout, __LOGGER__.info)

            if process.stderr:
                tg.start_soon(_drain_stream, process.stderr, __LOGGER__.error)

            return_code = await process.wait()

        direct_results = self._get_result(DIRECT_TEST_RESULT_FILE_NAME)
        invariant_results = self._get_result(INVARIANT_TEST_RESULT_FILE_NAME)
        return (
            return_code,
            await direct_results,
            await invariant_results,
        )

    async def get_version(self) -> str | None:
        """Get the version of the SDCcc executable."""
        result = await anyio.run_process([self.exe, '--version'], check=True, cwd=self.exe.parent)
        return result.stdout.decode(_common.ENCODING).strip() if result.stdout is not None else None
