"""tests for the checker tool module."""

import pathlib
import subprocess
import uuid
from unittest import mock

import anyio
import pytest

from pysdccc._checker_tool import (
    __LOGGER__,
    SdcccCheckerTool,
)
from pysdccc._common import _drain_stream


async def test_checker_tool_init_default_exe_not_found():
    """Test that the checker tool raises FileNotFoundError when exe is None and SDCcc is not downloaded."""
    with (
        mock.patch('pysdccc._common.get_checker_tool_exe_path', side_effect=FileNotFoundError),
        pytest.raises(FileNotFoundError, match='Have you downloaded SDCcc'),
    ):
        SdcccCheckerTool()


async def test_checker_tool_init_default_exe():
    """Test that the checker tool resolves the executable of the downloaded SDCcc version by default."""
    expected_exe = await anyio.Path(__file__).absolute()
    with mock.patch('pysdccc._common.get_checker_tool_exe_path', return_value=expected_exe):
        assert SdcccCheckerTool().exe == expected_exe


async def test_checker_tool_init():
    """Test that the checker tool is correctly initialized and validates the executable path."""
    abs_cwd = await anyio.Path().absolute()
    with pytest.raises(ValueError, match='Path to executable must be absolute'):
        SdcccCheckerTool(pathlib.Path())
    with pytest.raises(FileNotFoundError, match=f'No executable found under {pathlib.Path()}'):
        SdcccCheckerTool(abs_cwd)
    tool = SdcccCheckerTool(pathlib.Path(__file__))
    assert tool.exe == await anyio.Path(__file__).absolute()


async def test_checker_tool_prepare_command_relative_paths():
    """Test that the checker tool rejects relative mdib and reference paths."""
    tool = SdcccCheckerTool(pathlib.Path(__file__))
    absolute = await anyio.Path().absolute()
    with pytest.raises(ValueError, match='Path to mdib file must be absolute'):
        tool._prepare_command(mdib=anyio.Path(), reference=absolute, generate_reference=False)  # noqa: SLF001
    with pytest.raises(ValueError, match='Path to reference file must be absolute'):
        tool._prepare_command(mdib=absolute, reference=anyio.Path(), generate_reference=False)  # noqa: SLF001


async def test_checker_tool_prepare_command():
    """Test that the checker tool maps its arguments onto the command line options of the executable."""
    tool = SdcccCheckerTool(pathlib.Path(__file__))
    mdib = await anyio.Path(__file__).absolute()
    reference = (await anyio.Path().absolute()).joinpath(f'{uuid.uuid4().hex}.json')

    assert tool._prepare_command(mdib=mdib, reference=reference, generate_reference=False) == [  # noqa: SLF001
        '--mdibpath',
        str(mdib),
        '--refpath',
        str(reference),
    ]
    assert tool._prepare_command(mdib=mdib, reference=reference, generate_reference=True) == [  # noqa: SLF001
        '--mdibpath',
        str(mdib),
        '--refpath',
        str(reference),
        '--generateref',
    ]


@pytest.mark.parametrize('returncode', [0, 1, 2])
@pytest.mark.parametrize('generate_reference', [False, True])
async def test_checker_tool_run(returncode: int, generate_reference: bool):  # noqa: FBT001
    """Test that run passes the returncode through verbatim and logs stdout and stderr."""
    tool = SdcccCheckerTool(pathlib.Path(__file__))
    mdib = await anyio.Path(__file__).absolute()
    reference = (await anyio.Path().absolute()).joinpath(f'{uuid.uuid4().hex}.json')

    with (
        mock.patch('anyio.open_process') as mock_open_process,
        mock.patch('anyio.create_task_group') as mock_task_group,
    ):
        mock_open_process.return_value.__aenter__.return_value.wait = mock.AsyncMock(return_value=returncode)
        mock_start_soon = mock.MagicMock()
        mock_task_group.return_value.__aenter__.return_value.start_soon = mock_start_soon
        result = await tool.run(mdib=mdib, reference=reference, generate_reference=generate_reference)

    assert result == returncode
    mock_open_process.assert_called_once_with(
        [
            str(tool.exe),
            '--mdibpath',
            str(mdib),
            '--refpath',
            str(reference),
            *(['--generateref'] if generate_reference else []),
        ],
        cwd=str(tool.exe.parent),
    )
    expected_calls = [
        mock.call(_drain_stream, mock_open_process.return_value.__aenter__.return_value.stdout, __LOGGER__.info),
        mock.call(_drain_stream, mock_open_process.return_value.__aenter__.return_value.stderr, __LOGGER__.error),
    ]
    assert mock_start_soon.call_count == len(expected_calls)
    mock_start_soon.assert_has_calls(expected_calls)


async def test_checker_tool_run_additional_arguments():
    """Test that run forwards additional keyword arguments to the executable."""
    tool = SdcccCheckerTool(pathlib.Path(__file__))
    mdib = await anyio.Path(__file__).absolute()
    reference = (await anyio.Path().absolute()).joinpath(f'{uuid.uuid4().hex}.json')
    value = uuid.uuid4().hex

    with (
        mock.patch('anyio.open_process') as mock_open_process,
        mock.patch('anyio.create_task_group') as mock_task_group,
    ):
        mock_open_process.return_value.__aenter__.return_value.wait = mock.AsyncMock(return_value=0)
        mock_task_group.return_value.__aenter__.return_value.start_soon = mock.MagicMock()
        await tool.run(mdib=mdib, reference=reference, some_option=value)

    assert mock_open_process.call_args.args[0] == [
        str(tool.exe),
        '--some_option',
        value,
        '--mdibpath',
        str(mdib),
        '--refpath',
        str(reference),
    ]


async def test_checker_tool_run_relative_path():
    """Test that run rejects relative paths before starting the process."""
    tool = SdcccCheckerTool(pathlib.Path(__file__))
    with (
        mock.patch('anyio.open_process') as mock_open_process,
        pytest.raises(ValueError, match='Path to mdib file must be absolute'),
    ):
        await tool.run(mdib=pathlib.Path('mdib.xml'), reference=await anyio.Path().absolute())
    mock_open_process.assert_not_called()


async def test_checker_tool_get_version_expected():
    """Test that the checker tool correctly retrieves the version of the executable."""
    tool = SdcccCheckerTool(await anyio.Path(__file__).absolute())
    version = uuid.uuid4().hex
    with mock.patch('anyio.run_process') as mock_run_process:
        mock_run_process.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=version.encode(), stderr=b''
        )
        assert await tool.get_version() == version
    mock_run_process.assert_called_once_with([tool.exe, '--version'], check=True, cwd=tool.exe.parent)


async def test_checker_tool_get_version_error():
    """Test that the checker tool correctly raises CalledProcessError and provides exception info."""
    tool = SdcccCheckerTool(await anyio.Path(__file__).absolute())

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
        await tool.get_version()
    assert exc_info.value.cmd == cmd
    assert exc_info.value.returncode == returncode
    assert exc_info.value.stdout == stdout
    assert exc_info.value.stderr == stderr
    mock_run_process.assert_called_once_with([tool.exe, '--version'], check=True, cwd=tool.exe.parent)
