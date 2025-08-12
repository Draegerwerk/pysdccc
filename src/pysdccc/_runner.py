"""Implements the runner for the SDCcc executable.

This module provides the `SdcccRunner` class to manage and execute the SDCcc tests. It handles the configuration,
requirements, and execution of the SDCcc executable, as well as parsing the test results.

Classes
-------

SdcccRunner
    Runner for the SDCcc tests.

Functions
---------

check_requirements(provided: dict[str, dict[str, bool]], available: dict[str, dict[str, bool]]) -> None
    Check if the provided requirements are supported by the available requirements.

Usage
-----

.. code-block:: python

    from pysdccc import SdcccRunner
    import pathlib

    # Initialize the runner with the path to the SDCcc executable and the test run directory
    runner = SdcccRunner(
        exe=pathlib.Path("/absolute/path/to/sdccc-executable"),
        test_run_dir=pathlib.Path("/absolute/path/to/test-run-directory")
    )

    # Load the default configuration
    config = runner.get_config()

    # Load the default requirements
    requirements = runner.get_requirements()

    # Check user-provided requirements against the SDCcc provided requirements
    runner.check_requirements(pathlib.Path("/absolute/path/to/user-requirements.toml"))

    # Run the SDCcc executable with the specified configuration and requirements
    exit_code, direct_result, invariant_result = runner.run(
        config=pathlib.Path("/absolute/path/to/config.toml"),
        requirements=pathlib.Path("/absolute/path/to/requirements.toml"),
        timeout=3600  # 1 hour timeout
    )
"""

import functools
import pathlib
import typing

import anyio
import anyio.from_thread

from pysdccc import _async_runner, _common
from pysdccc._result_parser import TestSuite


class SdcccRunner:
    """Synchronous runner for SDCcc."""

    def __init__(self, test_run_dir: _common.PATH_TYPE, exe: _common.PATH_TYPE | None = None):
        """Initialize the SdcccRunner object.

        :param exe: The path to the SDCcc executable. Must be an absolute path.
        :param test_run_dir: The path to the directory where the test run results are to be stored. Must be an absolute
        path.
        :raises ValueError: If the provided paths are not absolute.
        """
        self.__async_runner = _async_runner.SdcccRunnerAsync(test_run_dir=test_run_dir, exe=exe)
        self.__portal_provider = anyio.from_thread.BlockingPortalProvider()

    @property
    def exe(self) -> pathlib.Path:
        """Get the path to the SDCcc executable."""
        return pathlib.Path(self.__async_runner.exe)

    @property
    def test_run_dir(self) -> pathlib.Path:
        """Get the path to the test run directory."""
        return pathlib.Path(self.__async_runner.test_run_dir)

    def get_config(self) -> dict[str, typing.Any]:
        """Get the default configuration.

        This method loads the default configuration from the SDCcc executable's directory.

        :return: A dictionary containing the configuration data.
        """
        with self.__portal_provider as portal:
            return portal.call(self.__async_runner.get_config)

    def get_requirements(self) -> dict[str, dict[str, bool]]:
        """Get the default requirements.

        This method loads the default requirements from the SDCcc executable's directory.

        :return: A dictionary containing the requirements data.
        """
        with self.__portal_provider as portal:
            return portal.call(self.__async_runner.get_requirements)

    def get_test_parameter(self) -> dict[str, typing.Any]:
        """Get the default test parameter.

        This method loads the default test parameters from the SDCcc executable's directory.

        :return: A dictionary containing the test parameter data.
        """
        with self.__portal_provider as portal:
            return portal.call(self.__async_runner.get_test_parameter)

    def check_requirements(self, path: _common.PATH_TYPE) -> None:
        """Check the requirements from the given file against the requirements provided by the SDCcc version.

        This method verifies that all the requirements specified in the user's requirements file are supported by the
        requirements provided by the SDCcc version. If any requirement is not found, a KeyError is raised.

        :param path: The path to the user's requirements file.
        :raises KeyError: If a standard or requirement provided by the user is not found in the SDCcc provided
        requirements.
        """
        with self.__portal_provider as portal:
            portal.call(self.__async_runner.check_requirements, path)

    def run(
        self,
        *,
        config: _common.PATH_TYPE,
        requirements: _common.PATH_TYPE,
        timeout: float | None = None,
        **kwargs: _common.CMD_TYPE,
    ) -> tuple[int, TestSuite | None, TestSuite | None]:
        """Run the SDCcc executable using the specified configuration and requirements.

        This method executes the SDCcc executable with the provided configuration and requirements files,
        and additional command line arguments. It logs the stdout and stderr of the process and waits for the
        process to complete or timeout.
        Checkout more parameter under https://github.com/draegerwerk/sdccc?tab=readme-ov-file#running-sdccc

        :param config: The path to the configuration file. Must be an absolute path.
        :param requirements: The path to the requirements file. Must be an absolute path.
        :param timeout: The timeout in seconds for the SDCcc process. If None, wait indefinitely.
        :param kwargs: Additional command line arguments to be passed to the SDCcc executable.
        :return: A tuple containing the returncode of the SDCcc process, parsed direct and invariant test results as
        TestSuite objects.
        :raises ValueError: If the provided paths are not absolute.
        :raises subprocess.TimeoutExpired: If the process is running longer than the timeout.
        """
        runner = functools.partial(self.__async_runner.run, config=config, requirements=requirements, **kwargs)
        with self.__portal_provider as portal:
            return portal.start_task_soon(runner).result(timeout=timeout)

    def get_version(self) -> str | None:
        """Get the version of the SDCcc executable."""
        with self.__portal_provider as portal:
            return portal.call(self.__async_runner.get_version)
