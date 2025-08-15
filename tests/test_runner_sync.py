"""tests for module runner.py."""

import pathlib
import subprocess
import uuid
from unittest import mock

import pytest

from pysdccc._runner import (
    SdcccRunner,
)
from pysdccc._runner_sync import SdcccRunnerSync


@mock.patch.object(SdcccRunner, '__init__', return_value=None)
def test_sdccc_runner_init(mock_init: mock.MagicMock):
    """Test that the runner is correctly initialized."""
    test_run_dir = pathlib.Path().absolute()
    exe = pathlib.Path(__file__)
    _ = SdcccRunnerSync(test_run_dir, exe)
    mock_init.assert_called_once_with(test_run_dir=test_run_dir, exe=exe)


@mock.patch.object(SdcccRunner, 'check_requirements')
def test_sdccc_runner_check_requirements(mock_check_requirements: mock.AsyncMock):
    """Test that the runner correctly checks the requirements."""
    path = pathlib.Path('requirements.toml')
    run = SdcccRunnerSync(
        pathlib.Path().absolute(),
        pathlib.Path(__file__).parent.joinpath('testversion').joinpath('sdccc.exe').absolute(),
    )
    run.check_requirements(path).result()
    mock_check_requirements.assert_called_once_with(path)


@mock.patch.object(SdcccRunner, 'get_config')
def test_configuration(mock_get_config: mock.AsyncMock):
    """Test that the runner correctly loads the configuration from the SDCcc executable's directory."""
    run = SdcccRunnerSync(
        pathlib.Path().absolute(),
        pathlib.Path(__file__).parent.joinpath('testversion/sdccc.exe').absolute(),
    )
    run.get_config().result()
    mock_get_config.assert_called_once_with()


@mock.patch.object(SdcccRunner, 'get_requirements')
def test_requirements(mock_get_requirements: mock.AsyncMock):
    """Test that the runner correctly loads the requirements from the SDCcc executable's directory."""
    run = SdcccRunnerSync(
        pathlib.Path().absolute(),
        pathlib.Path(__file__).parent.joinpath('testversion/sdccc.exe').absolute(),
    )
    run.get_requirements().result()
    mock_get_requirements.assert_called_once_with()


@mock.patch.object(SdcccRunner, 'get_version')
def test_sdccc_runner_get_version_expected(mock_get_version: mock.AsyncMock):
    """Test that the runner correctly retrieves the version of the SDCcc executable."""
    run = SdcccRunnerSync(pathlib.Path().absolute(), pathlib.Path(__file__).absolute())
    run.get_version().result()
    mock_get_version.assert_called_once_with()


def test_sdccc_runner_get_version_error():
    """Test that the runner correctly raises CalledProcessError and provides exception info."""
    runner = SdcccRunnerSync(pathlib.Path().absolute(), pathlib.Path(__file__).absolute())

    returncode = int(uuid.uuid4().int & 0xFFFFFFFF)
    stdout = uuid.uuid4().hex.encode()
    stderr = uuid.uuid4().hex.encode()
    cmd = [uuid.uuid4().hex]

    with (
        mock.patch.object(
            SdcccRunner,
            'get_version',
            side_effect=subprocess.CalledProcessError(returncode, cmd, output=stdout, stderr=stderr),
        ) as mock_get_version,
        pytest.raises(subprocess.CalledProcessError) as exc_info,
    ):
        runner.get_version().result()
    assert exc_info.value.cmd == cmd
    assert exc_info.value.returncode == returncode
    assert exc_info.value.stdout == stdout
    assert exc_info.value.stderr == stderr
    mock_get_version.assert_called_once_with()


@mock.patch.object(SdcccRunner, 'run')
def test_sdccc_runner_run(mock_run: mock.AsyncMock):
    """Test that the runner correctly runs SDCcc."""
    run = SdcccRunnerSync(pathlib.Path().absolute(), pathlib.Path(__file__).absolute())
    config = uuid.uuid4().hex
    requirements = uuid.uuid4().hex
    run.run(config=config, requirements=requirements).result()
    mock_run.assert_called_once_with(config=config, requirements=requirements)
