"""tests for async runner module."""

import pathlib
import re
import subprocess
import tomllib
import uuid
from unittest import mock

import anyio
import pytest

from pysdccc import _common
from pysdccc._result_parser import TestSuite
from pysdccc._runner import (
    __LOGGER__,
    DIRECT_TEST_RESULT_FILE_NAME,
    INVARIANT_TEST_RESULT_FILE_NAME,
    SdcccRunner,
    _drain_stream,
)

pytestmark = pytest.mark.anyio


async def test_drain_stream():
    """Test that the _drain_stream function correctly drains a stream and logs the output."""
    expected_message = f'{uuid.uuid4().hex.encode()} {uuid.uuid4().hex.encode()} \n'.encode(_common.ENCODING)
    send_stream, receive_stream = anyio.create_memory_object_stream[bytes]()
    log_messages = []

    def mock_log(message: object) -> None:
        log_messages.append(message)

    async with anyio.create_task_group() as tg:
        tg.start_soon(_drain_stream, receive_stream, mock_log)  # pyright: ignore[reportArgumentType]
        async with send_stream:
            await send_stream.send(expected_message)
    assert len(log_messages) == 1
    assert log_messages[0] == expected_message.decode(_common.ENCODING).strip()


async def test_sdccc_runner_init():
    """Test that the runner is correctly initialized and raises ValueError for relative paths."""
    with pytest.raises(ValueError, match='Path to test run directory must be absolute'):
        SdcccRunner(pathlib.Path(), pathlib.Path(__file__))
    with pytest.raises(ValueError, match='Path to executable must be absolute'):
        SdcccRunner(pathlib.Path().absolute(), pathlib.Path())
    with pytest.raises(FileNotFoundError, match=f'No executable found under {pathlib.Path()}'):
        SdcccRunner(pathlib.Path().absolute(), pathlib.Path().absolute())
    with pytest.raises(
        ValueError,
        match=re.escape(
            f'Test run directory "{pathlib.Path(__file__).absolute()}" is not a directory or does not exist'
        ),
    ):
        SdcccRunner(pathlib.Path(__file__).absolute(), pathlib.Path(__file__).absolute())
    runner = SdcccRunner(pathlib.Path().absolute(), pathlib.Path(__file__))
    assert runner.exe == await anyio.Path(__file__).absolute()
    assert runner.test_run_dir == await anyio.Path().absolute()
    with pytest.raises(ValueError, match='Path to requirements file must be absolute'):
        await runner._prepare_command(config=await anyio.Path().absolute(), requirements=anyio.Path())  # noqa: SLF001
    with pytest.raises(ValueError, match='Path to config file must be absolute'):
        await runner._prepare_command(config=anyio.Path(), requirements=await anyio.Path().absolute())  # noqa: SLF001
    with pytest.raises(ValueError, match=re.escape(f'{runner.test_run_dir} is not empty')):
        await runner._prepare_command(config=await anyio.Path().absolute(), requirements=await anyio.Path().absolute())  # noqa: SLF001


@mock.patch('tomllib.loads')
@mock.patch.object(SdcccRunner, 'get_requirements')
async def test_sdccc_runner_check_requirements(mock_get_requirements: mock.AsyncMock, mock_loads: mock.MagicMock):
    """Test that the runner correctly checks the requirements."""
    mock_get_requirements.return_value = {
        'test': {'test1': True, 'test2': False},
        'another_test': {'test3': True, 'test4': False},
    }
    mock_loads.return_value = {
        'test': {'test1': True, 'test2': False},
        'another_test': {'test3': True, 'test4': False},
    }
    runner = SdcccRunner(
        pathlib.Path().absolute(),
        pathlib.Path(__file__).parent.joinpath('testversion').joinpath('sdccc.exe').absolute(),
    )
    with (
        mock.patch('anyio.Path.read_text'),
        mock.patch('pysdccc._common.check_requirements') as mock_check_requirements,
    ):
        await runner.check_requirements(pathlib.Path('requirements.toml'))
    mock_check_requirements.assert_called_once_with(mock_loads.return_value, mock_get_requirements.return_value)


async def test_configuration():
    """Test that the runner correctly loads the configuration from the SDCcc executable's directory."""
    run = SdcccRunner(
        pathlib.Path().absolute(),
        pathlib.Path(__file__).parent.joinpath('testversion/sdccc.exe').absolute(),
    )
    loaded_config = await run.get_config()
    provided_config = """
[SDCcc]
CIMode=false
GraphicalPopups=true
TestExecutionLogging=true
EnableMessageEncodingCheck=true
SummarizeMessageEncodingErrors=true

[SDCcc.TLS]
FileDirectory="./configuration"
KeyStorePassword="whatever"
TrustStorePassword="whatever"
ParticipantPrivatePassword="dummypass"
EnabledProtocols = ["TLSv1.2", "TLSv1.3"]
EnabledCiphers = [
    # TLS 1.2
    "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_DHE_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_DHE_RSA_WITH_AES_256_GCM_SHA384",
    # TLS 1.3
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
]

[SDCcc.Network]
InterfaceAddress="127.0.0.1"
MaxWait=10
MulticastTTL=128

[SDCcc.Consumer]
Enable=true
DeviceEpr="urn:uuid:857bf583-8a51-475f-a77f-d0ca7de69b11"
# DeviceLocationBed="bed32"
# DeviceLocationPointOfCare="poc32"
# etc.

[SDCcc.Provider]
Enable=false

[SDCcc.gRPC]
ServerAddress="localhost:50051"

[SDCcc.TestParameter]
Biceps547TimeInterval=5
    """
    assert tomllib.loads(provided_config) == loaded_config


async def test_requirements():
    """Test that the runner correctly loads the requirements from the SDCcc executable's directory."""
    run = SdcccRunner(
        pathlib.Path().absolute(),
        pathlib.Path(__file__).parent.joinpath('testversion/sdccc.exe').absolute(),
    )
    loaded_config = await run.get_requirements()
    provided_config = """
[MDPWS]
R0006=false
R0008=true
R0010=true
R0011=true
R0012=true
R0013=true
R0014=true
R0015=true

[BICEPS]
R0007_0=true
R0021=true
R0023=true
R0025_0=true
R0029_0=true
R0033=true
R0034_0=true
R0038_0=true
R0055_0=false
R0062=true
R0064=true
R0066=true
R0068=true
R0069=true
R0097=true
R0098_0=true
R0100=false
R0101=true
R0104=true
R0105_0=true
R0116=true
R0119=false
R0124=true
R0125=true
R0133=true
R5003=true
R5006=true
B-6_0=true
B-128=false
B-284_0=true
B-402_0=true
C-5=true
C-7=true
C-11=true
C-12=true
C-13=true
C-14=true
C-15=true
C-55_0=true
C-62=true
R5024=true
R5025_0=true
R5039=true
R5040=true
R5041=true
R5042=true
R5046_0=true
R5051=true
R5052=true
R5053=true
5-4-7_0_0=true
5-4-7_1=true
5-4-7_2=true
5-4-7_3=true
5-4-7_4=true
5-4-7_5=true
5-4-7_6_0=true
5-4-7_7=true
5-4-7_8=true
5-4-7_9=true
5-4-7_10=true
5-4-7_11=true
5-4-7_12_0=true
5-4-7_13=true
5-4-7_14=true
5-4-7_15=true
5-4-7_16=true
5-4-7_17=true

[DPWS]
R0001=false
R0013=false
R0019=false
R0031=false
R0034=false
R0040=false

[GLUE]
13=true
8-1-3=true
R0010_0=true
R0011=true
R0012_0_0=true
R0013=false
R0034_0=true
R0036_0=true
R0042_0=true
R0056=true
R0072=false
R0078_0=true
R0080=true
    """
    assert tomllib.loads(provided_config) == loaded_config


async def test_parameter():
    """Test that the runner correctly loads the test parameters from the SDCcc executable's directory."""
    run = SdcccRunner(
        pathlib.Path().absolute(),
        pathlib.Path(__file__).parent.joinpath('testversion/sdccc.exe').absolute(),
    )
    loaded_config = await run.get_test_parameter()
    provided_config = """[TestParameter]
Biceps547TimeInterval=5"""
    assert tomllib.loads(provided_config) == loaded_config


async def test_parse_result():
    """Test that the runner correctly parses the test results from the SDCcc executable's directory."""
    invariant = (
        (
            'BICEPS.R6039',
            'Sends a get context states message with empty handle ref and verifies that the response '
            'contains all context states of the mdib.',
        ),
        (
            'BICEPS.R6040',
            'Verifies that for every known context descriptor handle the corresponding context states are returned.',
        ),
        (
            'BICEPS.R6041',
            'Verifies that for every known context state handle the corresponding context state is returned.',
        ),
        ('SDCccTestRunValidity', 'SDCcc Test Run Validity'),
    )
    direct = (
        (
            'MDPWS.R5039',
            'Sends a get context states message with empty handle ref and verifies that the response '
            'contains all context states of the mdib.',
        ),
        (
            'MDPWS.R5040',
            'Verifies that for every known context descriptor handle the corresponding context states are returned.',
        ),
        (
            'MDPWS.R5041',
            'Verifies that for every known context state handle the corresponding context state is returned.',
        ),
        ('SDCccTestRunValidity', 'SDCcc Test Run Validity'),
    )
    run = SdcccRunner(
        pathlib.Path(__file__).parent.joinpath('sdccc_example_results').absolute(), pathlib.Path(__file__).absolute()
    )
    direct_results = run._get_result(DIRECT_TEST_RESULT_FILE_NAME)  # noqa: SLF001
    invariant_results = run._get_result(INVARIANT_TEST_RESULT_FILE_NAME)  # noqa: SLF001

    def verify_suite(suite: TestSuite | None, data: tuple[tuple[str, str], ...]):
        assert isinstance(suite, TestSuite)
        assert len(data) == len(suite)

    verify_suite(await direct_results, direct)
    verify_suite(await invariant_results, invariant)


async def test_sdccc_runner_get_version_expected():
    """Test that the runner correctly retrieves the version of the SDCcc executable."""
    runner = SdcccRunner(pathlib.Path().absolute(), pathlib.Path(__file__).absolute())
    version = uuid.uuid4().hex
    with mock.patch('anyio.run_process') as mock_run_process:
        mock_run_process.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=version.encode(), stderr=b''
        )
        assert await runner.get_version() == version


async def test_sdccc_runner_get_version_error():
    """Test that the runner correctly raises CalledProcessError and provides exception info."""
    runner = SdcccRunner(pathlib.Path().absolute(), pathlib.Path(__file__).absolute())

    returncode = int(uuid.uuid4().int & 0xFFFFFFFF)  # ensure that the return code is a 32-bit integer
    stdout = uuid.uuid4().hex.encode()
    stderr = uuid.uuid4().hex.encode()
    cmd = [uuid.uuid4().hex]

    with (
        mock.patch(
            'anyio.run_process',
            side_effect=subprocess.CalledProcessError(returncode, cmd, output=stdout, stderr=stderr),
        ) as mock_run_process,
        pytest.raises(subprocess.CalledProcessError) as exc_info,
    ):
        await runner.get_version()
    assert exc_info.value.cmd == cmd
    assert exc_info.value.returncode == returncode
    assert exc_info.value.stdout == stdout
    assert exc_info.value.stderr == stderr
    mock_run_process.assert_called_once_with([runner.exe, '--version'], check=True, cwd=runner.exe.parent)


async def test_sdccc_runner_run_success():
    """Test that run returns (returncode, direct, invariant) if the process exits with a zero code."""
    config = pathlib.Path(__file__).parent.joinpath('test_version', 'configuration', 'config.toml')
    requirements = pathlib.Path(__file__).parent.joinpath('test_version', 'configuration', 'test_configuration.toml')
    async with anyio.TemporaryDirectory() as temp_dir:
        runner = SdcccRunner(temp_dir, pathlib.Path(__file__).absolute())
        returncode = 0
        direct_result = object()
        invariant_result = object()
        with (
            mock.patch.object(
                runner,
                '_get_result',
                side_effect=lambda file_name: direct_result
                if file_name == DIRECT_TEST_RESULT_FILE_NAME
                else invariant_result,
            ),
            mock.patch('anyio.open_process') as mock_open_process,
            mock.patch('anyio.create_task_group') as mock_task_group,
        ):
            mock_open_process.return_value.__aenter__.return_value.wait = mock.AsyncMock(return_value=returncode)
            mock_start_soon = mock.MagicMock()
            mock_task_group.return_value.__aenter__.return_value.start_soon = mock_start_soon
            result = await runner.run(config=config, requirements=requirements)
    assert result == (returncode, direct_result, invariant_result)
    mock_open_process.assert_called_once_with(
        [
            str(runner.exe),
            '--no_subdirectories',
            'true',
            '--test_run_directory',
            str(runner.test_run_dir),
            '--config',
            str(config),
            '--testconfig',
            str(requirements),
        ],
        cwd=str(runner.exe.parent),
    )
    expected_calls = [
        mock.call(_drain_stream, mock_open_process.return_value.__aenter__.return_value.stdout, __LOGGER__.info),
        mock.call(_drain_stream, mock_open_process.return_value.__aenter__.return_value.stderr, __LOGGER__.error),
    ]
    assert mock_start_soon.call_count == len(expected_calls)
    mock_start_soon.assert_has_calls(expected_calls)


async def test_sdccc_runner_run_nonzero():
    """Test that run returns (returncode, None, None) if the process exits with a non-zero code."""
    config = pathlib.Path(__file__).parent.joinpath('test_version', 'configuration', 'config.toml')
    requirements = pathlib.Path(__file__).parent.joinpath('test_version', 'configuration', 'test_configuration.toml')
    async with anyio.TemporaryDirectory() as temp_dir:
        runner = SdcccRunner(temp_dir, pathlib.Path(__file__).absolute())
        returncode = int(uuid.uuid4().int & 0xFFFFFFFF)  # ensure that the return code is a 32-bit integer
        with (
            mock.patch('anyio.open_process') as mock_open_process,
            mock.patch('anyio.create_task_group') as mock_task_group,
        ):
            mock_open_process.return_value.__aenter__.return_value.wait = mock.AsyncMock(return_value=returncode)
            mock_start_soon = mock.MagicMock()
            mock_task_group.return_value.__aenter__.return_value.start_soon = mock_start_soon
            result = await runner.run(config=config, requirements=requirements)
    assert result == (returncode, None, None)
    mock_open_process.assert_called_once_with(
        [
            str(runner.exe),
            '--no_subdirectories',
            'true',
            '--test_run_directory',
            str(runner.test_run_dir),
            '--config',
            str(config),
            '--testconfig',
            str(requirements),
        ],
        cwd=str(runner.exe.parent),
    )
    expected_calls = [
        mock.call(_drain_stream, mock_open_process.return_value.__aenter__.return_value.stdout, __LOGGER__.info),
        mock.call(_drain_stream, mock_open_process.return_value.__aenter__.return_value.stderr, __LOGGER__.error),
    ]
    assert mock_start_soon.call_count == len(expected_calls)
    mock_start_soon.assert_has_calls(expected_calls)
