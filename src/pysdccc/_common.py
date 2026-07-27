"""Contains commonly used constants and functions."""

import locale
import os
import pathlib
import sys
from collections.abc import Iterable, Mapping, Sequence

import anyio

DEFAULT_STORAGE_DIRECTORY = pathlib.Path(__file__).parent.joinpath('_sdccc')
"""Default directory to store the downloaded SDCcc versions."""

PATH_TYPE = str | os.PathLike[str]

ENCODING = 'utf-8' if sys.flags.utf8_mode else locale.getencoding()

SINGLE_CMD_TYPE = str | int | bool | pathlib.Path | anyio.Path
CMD_TYPE = SINGLE_CMD_TYPE | Iterable[str | int | pathlib.Path | anyio.Path] | None


def build_command(*args: str, **kwargs: CMD_TYPE) -> Sequence[str]:
    """Build the command string from the arguments and keyword arguments."""
    command = list(args)
    for arg, value in kwargs.items():
        if isinstance(value, SINGLE_CMD_TYPE):
            if value is True:
                command.append(f'--{arg}')
            elif value is False:
                continue  # ignore False flags
            else:
                command.append(f'--{arg}')
                command.append(str(value))
        elif isinstance(value, Iterable) and not isinstance(value, dict | bytes):
            for item in value:
                command.append(f'--{arg}')
                command.append(str(item))
        elif value is not None:
            err = f'Unsupported value type: {type(value)}'
            raise TypeError(err)
    return command


def _find_single_exe(local_path: PATH_TYPE, *, checker_tool: bool) -> os.PathLike[str]:
    """Find exactly one ``.exe`` in ``local_path``, selecting the runner or the checker tool.

    :param local_path: The local path to search for executables.
    :param checker_tool: If True, select the checker tool executable (name contains
                         :data:`CHECKER_TOOL_MARKER`); otherwise select the test runner executable.
    :return: The path to the matching executable file.
    :raises FileNotFoundError: If no matching executable or more than one matching executable is found.
    """
    files = [f for f in pathlib.Path(local_path).glob('*.exe') if f.is_file()]
    selected = [f for f in files if ('checker-tool' in f.name) == checker_tool]
    if len(selected) != 1:
        kind = 'checker tool' if checker_tool else 'runner'
        msg = f'Expected a single {kind} executable, got {selected} in path {local_path}'
        raise FileNotFoundError(msg)
    return selected[0]


def get_exe_path(local_path: PATH_TYPE) -> os.PathLike[str]:
    """Get the path to the SDCcc test runner executable.

    This function searches the specified local path for the SDCcc test runner executable (``*.exe`` whose name does not
    follow ``sdccc-internal-<version>.exe``). The checker tool executable, if present, is ignored.
    It expects exactly one such file to be present in the directory. If no such file or more than one file is found,
    a FileNotFoundError is raised.

    :param local_path: The local path where the SDCcc executable is expected to be found.
    :return: The path to the SDCcc test runner executable file.
    :raises FileNotFoundError: If no executable file or more than one executable file is found in the specified path.
    """
    return _find_single_exe(local_path, checker_tool=False)


def get_checker_tool_exe_path(local_path: PATH_TYPE) -> os.PathLike[str]:
    """Get the path to the SDCcc checker tool executable.

    This function searches the specified local path for the SDCcc checker tool executable (``*.exe`` whose name contains
    ``sdccc-internal-checker-tool-<version>.exe``). It expects exactly one such file to be present in the directory.
    If no such file or more than one file is found, a FileNotFoundError is raised. Older SDCcc releases that ship only
    the test runner do not contain a checker tool, so this raises for those installations.

    :param local_path: The local path where the SDCcc checker tool executable is expected to be found.
    :return: The path to the SDCcc checker tool executable file.
    :raises FileNotFoundError: If no checker tool executable or more than one is found in the specified path.
    """
    return _find_single_exe(local_path, checker_tool=True)


def check_requirements(provided: Mapping[str, Mapping[str, bool]], available: Mapping[str, Mapping[str, bool]]) -> None:
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


def is_remote_path(path: PATH_TYPE) -> bool:
    """Check if the given path is a remote URL.

    :param path: The path to be checked.
    :return: True if the path is a remote URL, False otherwise.
    """
    as_lower_path = str(path).lower()
    return as_lower_path.startswith(('http://', 'https://'))
