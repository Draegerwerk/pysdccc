"""Implements the synchronous runner for the SDCcc executable."""

import concurrent.futures
import functools
import pathlib
import sys
import typing

import anyio
import anyio.from_thread

from pysdccc import _common, _runner
from pysdccc._result_parser import TestSuite

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated


@deprecated('Prefer using the async version of the runner instead.')
class SdcccRunnerSync:
    """Synchronous runner for SDCcc."""

    def __init__(self, test_run_dir: _common.PATH_TYPE, exe: _common.PATH_TYPE | None = None):
        """Initialize the SdcccRunner object.

        :param exe: The path to the SDCcc executable. Must be an absolute path.
        :param test_run_dir: The path to the directory where the test run results are to be stored. Must be an absolute
        path.
        :raises ValueError: If the provided paths are not absolute.
        """
        self.__async_runner = _runner.SdcccRunner(test_run_dir=test_run_dir, exe=exe)
        self.__portal_provider = anyio.from_thread.BlockingPortalProvider()

    @property
    def exe(self) -> pathlib.Path:
        """Get the path to the SDCcc executable."""
        return pathlib.Path(self.__async_runner.exe)

    @property
    def test_run_dir(self) -> pathlib.Path:
        """Get the path to the test run directory."""
        return pathlib.Path(self.__async_runner.test_run_dir)

    def get_config(self) -> concurrent.futures.Future[dict[str, typing.Any]]:
        """Get the default configuration.

        This method loads the default configuration from the SDCcc executable's directory.

        :return: A dictionary containing the configuration data.
        """
        with self.__portal_provider as portal:
            return portal.start_task_soon(self.__async_runner.get_config)

    def get_requirements(self) -> concurrent.futures.Future[dict[str, dict[str, bool]]]:
        """Get the default requirements.

        This method loads the default requirements from the SDCcc executable's directory.

        :return: A dictionary containing the requirements data.
        """
        with self.__portal_provider as portal:
            return portal.start_task_soon(self.__async_runner.get_requirements)

    def get_test_parameter(self) -> concurrent.futures.Future[dict[str, typing.Any]]:
        """Get the default test parameter.

        This method loads the default test parameters from the SDCcc executable's directory.

        :return: A dictionary containing the test parameter data.
        """
        with self.__portal_provider as portal:
            return portal.start_task_soon(self.__async_runner.get_test_parameter)

    def check_requirements(self, path: _common.PATH_TYPE) -> concurrent.futures.Future[None]:
        """Check the requirements from the given file against the requirements provided by the SDCcc version.

        This method verifies that all the requirements specified in the user's requirements file are supported by the
        requirements provided by the SDCcc version. If any requirement is not found, a KeyError is raised.

        :param path: The path to the user's requirements file.
        :raises KeyError: If a standard or requirement provided by the user is not found in the SDCcc provided
        requirements.
        """
        with self.__portal_provider as portal:
            return portal.start_task_soon(self.__async_runner.check_requirements, path)

    def run(
        self,
        *,
        config: _common.PATH_TYPE,
        requirements: _common.PATH_TYPE,
        **kwargs: _common.CMD_TYPE,
    ) -> concurrent.futures.Future[tuple[int, TestSuite | None, TestSuite | None]]:
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
        :raises subprocess.TimeoutExpired: If the process is running longer than the timeout.
        """
        runner = functools.partial(self.__async_runner.run, config=config, requirements=requirements, **kwargs)
        with self.__portal_provider as portal:
            return portal.start_task_soon(runner)

    def get_version(self) -> concurrent.futures.Future[str | None]:
        """Get the version of the SDCcc executable."""
        with self.__portal_provider as portal:
            return portal.start_task_soon(self.__async_runner.get_version)
