"""Tests for the _common module."""

import pathlib
import uuid
from collections.abc import Mapping
from unittest import mock

import anyio
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
    value6 = anyio.Path(uuid.uuid4().hex)
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
        key6=value6,
        key7=None,
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
        '--key6',
        str(value6),
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


@pytest.mark.parametrize(
    ('provided', 'available', 'should_raise'),
    [
        pytest.param(
            {'biceps': {'b1': True}},
            {'biceps': {'b1': True, 'b2': True}},
            False,
            id='all_requirements_present_and_enabled',
        ),
        pytest.param(
            {'biceps': {'b3': True}}, {'biceps': {'b1': True, 'b2': True}}, True, id='requirement_missing_in_available'
        ),
        pytest.param(
            {'biceps': {'b1': True, 'b3': False}},
            {'biceps': {'b1': True, 'b2': True}},
            False,
            id='requirement_disabled_in_provided',
        ),
        pytest.param({'mdpws': {'m1': True}}, {'biceps': {'b1': True}}, True, id='standard_missing_in_available'),
        pytest.param({'biceps': {'b1': True}}, {'biceps': {'b1': False}}, True, id='requirement_disabled_in_available'),
        pytest.param({'biceps': {'b1': False}}, {'biceps': {'b1': True}}, False, id='no_requirements_enabled'),
    ],
)
def test_check_requirements(
    provided: Mapping[str, Mapping[str, bool]], available: Mapping[str, Mapping[str, bool]], *, should_raise: bool
):
    """Test the _common.check_requirements function for correct validation of requirements.

    This test parametrizes several scenarios to verify that the function correctly raises a KeyError when the provided
    requirements are not met by the available requirements, and does not raise when requirements are satisfied.

    Scenarios covered:
    - Requirement is disabled in the provided requirements.
    - Standard is missing in the available requirements.
    - Requirement is disabled in the available requirements.
    - No requirements are enabled.

    For each scenario, if should_raise is True, the test expects a KeyError to be raised.
    Otherwise, it expects the function to complete without error.
    """
    if should_raise:
        with pytest.raises(KeyError):
            _common.check_requirements(provided, available)
    else:
        _common.check_requirements(provided, available)
