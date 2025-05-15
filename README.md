# pysdccc

This python packages provides a convenient way to execute the [SDCcc test suite](https://github.com/Draegerwerk/sdccc/).

This wrapper is only compatible with SDCcc versions later than [internal-baseline-001](https://github.com/Draegerwerk/SDCcc/releases/tag/internal-baseline-001).

## Installation

Download from pypi using `pip install pysdccc`. There is also an option to use this via the command line by installing `pysdccc[cli]`.

### Development

For this open source project the [Contributor License Agreement](Contributor_License_Agreement.md) governs all relevant activities and your contributions. By contributing to the project you agree to be bound by this Agreement and to licence your work accordingly.

1. clone the repository
2. install dependencies, e.g. with [`uv sync --dev --all-extras`](https://docs.astral.sh/uv/reference/cli/#uv-sync)

## Usage

### Quick start

```python
import pathlib
import subprocess

import pysdccc


def main():
    if not pysdccc.is_downloaded("my-specific-version"):
        pysdccc.download("https://url/to/sdccc.zip")

    runner = pysdccc.SdcccRunner(
        pathlib.Path("/path/to/sdccc/result/directory"),
    )

    try:
        # https://github.com/Draegerwerk/SDCcc/?tab=readme-ov-file#exit-codes
        return_code, direct_result, invariant_result = runner.run(
            config=pathlib.Path("/path/to/configuration/file.toml"),
            requirements=pathlib.Path("/path/to/requirements/file.toml"),
        )
    except subprocess.TimeoutExpired:
        print("Timeout occurred")
        return

    if direct_result is None or invariant_result is None:
        print("No result file available")
        return

    for test_case in direct_result + invariant_result:
        print(f"{test_case.name}: {test_case.is_passed}")
```
If you look for an async version

```python
import pathlib

import pysdccc


async def main():
    if not await pysdccc.ais_downloaded("my-specific-version"):
        await pysdccc.adownload("https://url/to/sdccc.zip")

    runner = pysdccc.SdcccRunnerAsync(
        pathlib.Path("/path/to/sdccc/result/directory"),
    )

    # https://github.com/Draegerwerk/SDCcc/?tab=readme-ov-file#exit-codes
    return_code, direct_result, invariant_result = await runner.run(
        config=pathlib.Path("/path/to/configuration/file.toml"),
        requirements=pathlib.Path("/path/to/requirements/file.toml"),
    )

    # checkout example from above ...
```

### Download an SDCcc executable

Check out `pysdccc.download` or `pysdccc.adownload`. If the command line interface of `pysdccc` is installed, the zipped source of SDCcc can be installed using this command: `pysdccc install https://url/to/sdccc.zip`

### Create configuration file

Configure the test consumer. Check the [test consumer configuration](https://github.com/Draegerwerk/SDCcc/?tab=readme-ov-file#test-consumer-configuration) for more information.

```python
import pathlib

import toml  # has to be installed by the user

import pysdccc

config = {
    'SDCcc': {
        ...  # add all relevant config parameter
    }
}
config_path = pathlib.Path('/path/to/configuration/file.toml')
config_path.write_text(toml.dumps(config))

runner = pysdccc.SdcccRunner(
    pathlib.Path('/path/to/sdccc/result/directory'),
)

runner.run(
    config=config_path,
    requirements=pathlib.Path('/path/to/requirements/file.toml'),
)

# or if you have already downloaded SDCcc
config = runner.get_config()  # load default configuration
config['SDCcc']['Consumer']['DeviceEpr'] = "urn:uuid:12345678-1234-1234-1234-123456789012"  # e.g. change device epr
# save and run as above
```

### Create requirements file

Enable or disable specific requirements. Check the [test requirements](https://github.com/Draegerwerk/SDCcc/?tab=readme-ov-file#enabling-tests) for more information.

```python
import pathlib

import toml  # has to be installed by the user

import pysdccc

requirements = {
    # the standard name is the key, the requirement from the standard is the value
    'BICEPS': {
        ...  # add all requirements to be tested
    }
}
requirements_path = pathlib.Path('/path/to/requirement/file.toml')
requirements_path.write_text(toml.dumps(requirements))

runner = pysdccc.SdcccRunner(
    pathlib.Path('/path/to/sdccc/result/directory'),
)
# optionally, check whether you did not add a requirement that is not available
runner.check_requirements(requirements_path)
runner.run(
    config=pathlib.Path('/path/to/configuration/file.toml'),
    requirements=requirements_path,
)

# or, if you have already downloaded SDCcc
requirements = runner.get_requirements()  # load default configuration
requirements['BICEPS']['R0033'] = False  # e.g. disable biceps R0033
# save and run as above
```

### Create test parameter configuration

Some tests require individual parameters. Check the [test parameter configuration](https://github.com/Draegerwerk/SDCcc/?tab=readme-ov-file#test-parameter-configuration) for more information.

```python
import pathlib

import toml  # has to be installed by the user

import pysdccc

testparameter_config = {
    'TestParameter': {
        ...
    }
}
testparameter_config_path = pathlib.Path('/path/to/test_parameter/file.toml')
testparameter_config_path.write_text(toml.dumps(testparameter_config))

runner = pysdccc.SdcccRunner(
    pathlib.Path('/path/to/sdccc/result/directory'),
)
runner.run(
    config=pathlib.Path('/path/to/configuration/file.toml'),
    requirements=pathlib.Path('/path/to/requirements/file.toml'),
    testparam=testparameter_config_path,
)

# or, if you have already downloaded SDCcc
testparameter_config = runner.get_test_parameter()  # load default configuration
testparameter_config['TestParameter']['Biceps547TimeInterval'] = 10
# save and run as above
```

### Execute SDCcc from command-line interface (cli)

There exists a cli wrapper for the SDCcc executable. If `pysdccc[cli]` is installed, `sdccc` can be used to execute arbitrary SDCcc commands, e.g. `sdccc --version`. More information can be found [here](https://github.com/draegerwerk/sdccc?tab=readme-ov-file#running-sdccc).

## Notices

`pysdccc` is not intended for use in medical products, clinical trials, clinical studies, or in clinical routine.

### ISO 9001

`pysdccc` was not developed according to ISO 9001.

## License

[MIT](https://choosealicense.com/licenses/mit/)
