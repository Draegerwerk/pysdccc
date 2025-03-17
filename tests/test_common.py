"""Tests for the _common module."""

import pathlib
import uuid

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
    key1 = uuid.uuid4().hex
    key2 = [uuid.uuid4().hex, uuid.uuid4().hex]
    key3 = (uuid.uuid4().hex, uuid.uuid4().hex)
    key4 = {uuid.uuid4().hex, uuid.uuid4().hex}
    key5 = pathlib.Path(uuid.uuid4().hex)
    _key4_iter = iter(key4)
    assert _common.build_command(
        arg1,
        arg2,
        flag1=True,
        flag2=False,
        key1=key1,
        key2=key2,
        key3=key3,
        key4=key4,
        key5=key5,
        key6=None,
    ) == [
        arg1,
        arg2,
        '--flag1',
        '--key1',
        key1,
        '--key2',
        key2[0],
        '--key2',
        key2[1],
        '--key3',
        key3[0],
        '--key3',
        key3[1],
        '--key4',
        next(_key4_iter),
        '--key4',
        next(_key4_iter),
        '--key5',
        str(key5),
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
