import locale
import os
import pathlib
import sys
import typing
from collections.abc import Iterable

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
