"""Contains commonly used constants and functions."""

import locale
import os
import pathlib
import sys
from collections.abc import Iterable

DEFAULT_STORAGE_DIRECTORY = pathlib.Path(__file__).parent.joinpath('_sdccc')
"""Default directory to store the downloaded SDCcc versions."""

PATH_TYPE = str | os.PathLike[str]

ENCODING = 'utf-8' if sys.flags.utf8_mode else locale.getencoding()

SINGLE_CMD_TYPE = str | int | bool | pathlib.Path
CMD_TYPE = SINGLE_CMD_TYPE | Iterable[str | int | pathlib.Path] | None


def build_command(*args: str, **kwargs: CMD_TYPE) -> list[str]:
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


def get_exe_path(local_path: pathlib.Path) -> pathlib.Path:
    """Get the path to the SDCcc executable.

    This function searches the specified local path for the SDCcc executable file. It expects exactly one executable
    file matching the pattern "sdccc-*.exe" to be present in the directory. If no such file or more than one file is
    found, a FileNotFoundError is raised.

    :param local_path: The local path where the SDCcc executable is expected to be found.
    :return: The path to the SDCcc executable file.
    :raises FileNotFoundError: If no executable file or more than one executable file is found in the specified path.
    """
    files = [f for f in local_path.glob('*.exe') if f.is_file()]
    if len(files) != 1:
        msg = f'Expected a single executable file, got {files} in path {local_path}'
        raise FileNotFoundError(msg)
    return files[0]
