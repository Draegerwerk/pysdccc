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

import pathlib
import subprocess
import sys
import tomllib
import typing

import anyio

from pysdccc import _common
from pysdccc._result_parser import TestSuite

DIRECT_TEST_RESULT_FILE_NAME = 'TEST-SDCcc_direct.xml'
INVARIANT_TEST_RESULT_FILE_NAME = 'TEST-SDCcc_invariant.xml'


def check_requirements(provided: dict[str, dict[str, bool]], available: dict[str, dict[str, bool]]) -> None:
    """Check if the provided requirements are supported by the available requirements.

    This function verifies that all the requirements specified in the `provided` dictionary are supported by the
    requirements in the `available` dictionary. If any requirement in `provided` is not found in `available`, a KeyError
    is raised.

    :param provided: A dictionary of provided requirements to be verified. The keys are standard names, and the values
                     are dictionaries where the keys are requirement IDs and the values are booleans indicating whether
                     the requirement is enabled.
    :param available: A dictionary of available requirements provided by SDCcc. The keys are standard names, and the
                      values are dictionaries where the keys are requirement IDs and the values are booleans indicating
                      whether the requirement is enabled.
    :raise KeyError: If a standard or requirement provided by the user is not found in the SDCcc provided requirements.
    """
    for standard, requirements in provided.items():
        if standard not in available:
            msg = f'Unsupported standard "{standard}". Supported standards are "{list(available)}"'
            raise KeyError(msg)
        provided_enabled = [req for req, enabled in requirements.items() if enabled]
        available_enabled = [a for a, enabled in available[standard].items() if enabled]
        for req in provided_enabled:
            if req not in available_enabled:
                msg = f'Requirement id "{standard}.{req}" not found'
                raise KeyError(msg)


class _BaseRunner:
    """Runner for the SDCcc tests.

    This class provides methods to manage and execute the SDCcc tests. It handles the configuration, requirements,
    and execution of the SDCcc executable, as well as parsing the test results.
    """

    def __init__(self, test_run_dir: _common.PATH_TYPE, exe: _common.PATH_TYPE | None = None):
        """Initialize the SdcccRunner object.

        :param exe: The path to the SDCcc executable. Must be an absolute path.
        :param test_run_dir: The path to the directory where the test run results are to be stored. Must be an absolute
        path.
        :raises ValueError: If the provided paths are not absolute.
        """
        try:
            self.exe = (
                pathlib.Path(exe)
                if exe is not None
                else _common.get_exe_path(_common.DEFAULT_STORAGE_DIRECTORY).absolute()
            )
        except FileNotFoundError as e:
            msg = 'Have you downloaded SDCcc?'
            raise FileNotFoundError(msg) from e
        if not self.exe.is_absolute():
            msg = f'Path to executable must be absolute but is {self.exe}'
            raise ValueError(msg)
        if not self.exe.is_file():
            msg = f'No executable found under {self.exe}'
            raise FileNotFoundError(msg)
        self.test_run_dir = pathlib.Path(test_run_dir)
        if not self.test_run_dir.is_absolute():
            msg = f'Path to test run directory must be absolute but is {self.test_run_dir}'
            raise ValueError(msg)
        if not self.test_run_dir.is_dir():
            msg = f'Test run directory "{self.test_run_dir}" is not a directory or does not exist'
            raise ValueError(msg)

    def get_config(self) -> dict[str, typing.Any]:
        """Get the default configuration.

        This method loads the default configuration from the SDCcc executable's directory.

        :return: A dictionary containing the configuration data.
        """
        return tomllib.loads(self.exe.parent.joinpath('configuration').joinpath('config.toml').read_text())

    def get_requirements(self) -> dict[str, dict[str, bool]]:
        """Get the default requirements.

        This method loads the default requirements from the SDCcc executable's directory.

        :return: A dictionary containing the requirements data.
        """
        return tomllib.loads(self.exe.parent.joinpath('configuration').joinpath('test_configuration.toml').read_text())

    def get_test_parameter(self) -> dict[str, typing.Any]:
        """Get the default test parameter.

        This method loads the default test parameters from the SDCcc executable's directory.

        :return: A dictionary containing the test parameter data.
        """
        return tomllib.loads(self.exe.parent.joinpath('configuration').joinpath('test_parameter.toml').read_text())

    def check_requirements(self, path: pathlib.Path) -> None:
        """Check the requirements from the given file against the requirements provided by the SDCcc version.

        This method verifies that all the requirements specified in the user's requirements file are supported by the
        requirements provided by the SDCcc version. If any requirement is not found, a KeyError is raised.

        :param path: The path to the user's requirements file.
        :raises KeyError: If a standard or requirement provided by the user is not found in the SDCcc provided
        requirements.
        """
        sdccc_provided_requirements = self.get_requirements()
        user_provided_requirements = tomllib.loads(path.read_text())
        check_requirements(user_provided_requirements, sdccc_provided_requirements)

    def _get_result(self, file_name: str) -> TestSuite | None:
        """Get the parsed results of the test run.

        This method reads the direct and invariant test result files from the test run directory and returns them
        as TestSuite objects.

        :return: A tuple containing the parsed direct and invariant test results as TestSuite objects.
        """
        test_result_dir = self.test_run_dir.joinpath(file_name)
        if not test_result_dir.exists():
            return None
        return TestSuite.from_file(test_result_dir)

    def _prepare_command(
        self,
        *args: str,
        config: pathlib.Path,
        requirements: pathlib.Path,
        **kwargs: _common.CMD_TYPE,
    ) -> list[str]:
        if not config.is_absolute():
            msg = 'Path to config file must be absolute'
            raise ValueError(msg)
        if not requirements.is_absolute():
            msg = 'Path to requirements file must be absolute'
            raise ValueError(msg)
        if list(self.test_run_dir.iterdir()):
            msg = f'{self.test_run_dir} is not empty'
            raise ValueError(msg)

        kwargs['no_subdirectories'] = 'true'
        kwargs['test_run_directory'] = self.test_run_dir
        kwargs['config'] = config
        kwargs['testconfig'] = requirements
        return _common.build_command(*args, **kwargs)


class SdcccRunner(_BaseRunner):
    """Synchronous runner for SDCcc."""

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
        command = self._prepare_command(
            str(self.exe),
            config=pathlib.Path(config),
            requirements=pathlib.Path(requirements),
            **kwargs,
        )
        try:
            return_code = subprocess.run(command, timeout=timeout, check=True, cwd=self.exe.parent).returncode  # noqa: S603
        except subprocess.CalledProcessError as e:
            return_code = e.returncode
        return (
            return_code,
            self._get_result(DIRECT_TEST_RESULT_FILE_NAME),
            self._get_result(INVARIANT_TEST_RESULT_FILE_NAME),
        )

    def get_version(self) -> str:
        """Get the version of the SDCcc executable."""
        # use capture_output = True to get stdout and stderr instead of check_output which only collects stdout
        process = subprocess.run([str(self.exe), '--version'], check=True, capture_output=True, cwd=self.exe.parent)  # noqa: S603
        return process.stdout.decode(_common.ENCODING).strip()


class SdcccRunnerAsync(_BaseRunner):
    """Asynchronous runner for SDCcc."""

    def __init__(self, test_run_dir: _common.PATH_TYPE, exe: _common.PATH_TYPE | None = None):
        """Initialize the SdcccRunnerAsync object.

        :param exe: The path to the SDCcc executable. Must be an absolute path.
        :param test_run_dir: The path to the directory where the test run results are to be stored. Must be an absolute
        path.
        :raises ValueError: If the provided paths are not absolute.
        """
        super().__init__(test_run_dir=test_run_dir, exe=exe)

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
        :raises TimeoutError: If the process is running longer than the timeout.
        """
        command = self._prepare_command(
            str(self.exe), config=pathlib.Path(config), requirements=pathlib.Path(requirements), **kwargs
        )
        try:
            return_code = (
                await anyio.run_process(command, check=True, cwd=self.exe.parent, stdout=sys.stdout, stderr=sys.stderr)
            ).returncode
        except subprocess.CalledProcessError as e:
            return_code = e.returncode

        return (
            return_code,
            self._get_result(DIRECT_TEST_RESULT_FILE_NAME),
            self._get_result(INVARIANT_TEST_RESULT_FILE_NAME),
        )

    async def get_version(self) -> str | None:
        """Get the version of the SDCcc executable."""
        result = await anyio.run_process([self.exe, '--version'], check=True, cwd=self.exe.parent)
        return result.stdout.decode(_common.ENCODING).strip() if result.stdout is not None else None
