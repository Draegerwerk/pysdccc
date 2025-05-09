"""Tests for the _common module."""

import pathlib
import uuid
from unittest import mock

import pytest

from pysdccc import _common


def test_build_command_no_args():
    """Test that the build_command function works with no arguments."""
    assert _common.build_command() == []


def test_build_command_with_args():
    """Test that the build_command function works with arguments."""
    arg1 = uuid.uuid4().hex
    arg2 = uuid.uuid4().hex
    assert _common.build_command(arg1, arg2) == [arg1, arg2]


def test_build_command_with_args_and_kwargs():
    """Test that the build_command function works with arguments and keyword arguments."""
    arg1 = uuid.uuid4().hex
    arg2 = uuid.uuid4().hex
    value1 = uuid.uuid4().hex
    value2 = [uuid.uuid4().hex, uuid.uuid4().hex]
    value3 = (uuid.uuid4().hex, uuid.uuid4().hex)
    value4 = {uuid.uuid4().hex, uuid.uuid4().hex}
    value5 = pathlib.Path(uuid.uuid4().hex)
    _key4_iter = iter(value4)
    assert _common.build_command(
        arg1,
        arg2,
        flag1=True,
        flag2=False,
        key1=value1,
        key2=value2,
        key3=value3,
        key4=value4,
        key5=value5,
        key6=None,
    ) == [
        arg1,
        arg2,
        '--flag1',
        '--key1',
        value1,
        '--key2',
        value2[0],
        '--key2',
        value2[1],
        '--key3',
        value3[0],
        '--key3',
        value3[1],
        '--key4',
        next(_key4_iter),
        '--key4',
        next(_key4_iter),
        '--key5',
        str(value5),
    ]


def test_raise_not_implemented_error():
    """Test that the build_command function raises TypeError for unsupported value types."""
    with pytest.raises(TypeError):
        _common.build_command(key=bytes(uuid.uuid4().hex, 'utf-8'))

    with pytest.raises(TypeError):
        _common.build_command(key={'key': uuid.uuid4().hex})

    class CustomType:
        pass

    with pytest.raises(TypeError):
        _common.build_command(key=CustomType())  # pyright: ignore [reportArgumentType]


def test_get_exe_path():
    """Test that the executable path is correctly identified."""
    expected_path = pathlib.Path('sdccc-1.0.0.exe')
    assert not expected_path.exists()

    with (
        mock.patch('pathlib.Path.glob', return_value=[expected_path]),
        mock.patch('pathlib.Path.is_file', return_value=True),
    ):
        assert _common.get_exe_path(expected_path) == expected_path

    with pytest.raises(FileNotFoundError):
        _common.get_exe_path(expected_path)
