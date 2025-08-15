# pysdccc

This python packages provides a convenient way to execute the [SDCcc test suite](https://github.com/Draegerwerk/sdccc/).

This wrapper is only compatible with SDCcc versions later than [internal-baseline-001](https://github.com/Draegerwerk/SDCcc/releases/tag/internal-baseline-001).

## Installation

Download from pypi using `pip install pysdccc`. There is also an option to use this via the command line by installing `pysdccc[cli]`.

### Development

For this open source project the [Contributor License Agreement](Contributor_License_Agreement.md) governs all relevant activities and your contributions. By contributing to the project you agree to be bound by this Agreement and to licence your work accordingly.

1. clone the repository
2. install dependencies, e.g. with [`uv sync --dev`](https://docs.astral.sh/uv/reference/cli/#uv-sync)

## Usage

### Quick start

```python
import pysdccc


async def main():
    if not await pysdccc.is_downloaded("my-specific-version"):
        await pysdccc.download("https://url/to/sdccc.zip")

    runner = pysdccc.SdcccRunner("/path/to/sdccc/result/directory")

    # https://github.com/Draegerwerk/SDCcc/?tab=readme-ov-file#exit-codes
    return_code, direct_result, invariant_result = await runner.run(
        config="/path/to/configuration/file.toml",
        requirements="/path/to/requirements/file.toml",
    )
    if direct_result is None or invariant_result is None:
        print("No result file available")
        return

    for test_case in direct_result + invariant_result:
        print(f"{test_case.test_identifier}: {test_case.is_passed}")
```
If you look for a synchronous version. Please note this is deprecated. The async methods are the preferred way.

```python
import pathlib

import pysdccc


async def main():
    if not pysdccc.is_downloaded_sync("my-specific-version"):
        pysdccc.download_sync("https://url/to/sdccc.zip")

    runner = pysdccc.SdcccRunnerSync("/path/to/sdccc/result/directory")

    # https://github.com/Draegerwerk/SDCcc/?tab=readme-ov-file#exit-codes
    return_code, direct_result, invariant_result = runner.run(
        config="/path/to/configuration/file.toml",
        requirements="/path/to/requirements/file.toml",
    ).result(timeout=60)  # use .result(timeout=...) to wait for the result in a synchronous way

    # checkout example from above ...
```

### Create configuration file

Configure the test consumer. Check the [test consumer configuration](https://github.com/Draegerwerk/SDCcc/?tab=readme-ov-file#test-consumer-configuration) for more information.

```python
import anyio
import toml  # has to be installed by the user

import pysdccc


async def main():
    config = {
        'SDCcc': {
            ...  # add all relevant config parameter
        }
    }
    config_path = anyio.Path('/path/to/configuration/file.toml')
    await config_path.write_text(toml.dumps(config))

    runner = pysdccc.SdcccRunner('/path/to/sdccc/result/directory')

    await runner.run(config=config_path, requirements='/path/to/requirements/file.toml')

    # or if you have already downloaded SDCcc
    config = await runner.get_config()  # load default configuration
    config['SDCcc']['Consumer']['DeviceEpr'] = "urn:uuid:12345678-1234-1234-1234-123456789012"  # e.g. change device epr
    # save and run as above
```

### Create requirements file

Enable or disable specific requirements. Check the [test requirements](https://github.com/Draegerwerk/SDCcc/?tab=readme-ov-file#enabling-tests) for more information.

```python
import anyio
import toml  # has to be installed by the user

import pysdccc


async def main():
    requirements = {
        # the standard name is the key, the requirement from the standard is the value
        'BICEPS': {
            ...  # add all requirements to be tested
        }
    }
    requirements_path = anyio.Path('/path/to/requirement/file.toml')
    await requirements_path.write_text(toml.dumps(requirements))

    runner = pysdccc.SdcccRunner('/path/to/sdccc/result/directory')

    # optionally, check whether you did not add a requirement that is not available
    await runner.check_requirements(requirements_path)
    await runner.run('/path/to/configuration/file.toml', requirements=requirements_path)

    # or, if you have already downloaded SDCcc
    requirements = await runner.get_requirements()  # load default configuration
    requirements['BICEPS']['R0033'] = False  # e.g. disable biceps R0033
    # save and run as above
```

### Create test parameter configuration

Some tests require individual parameters. Check the [test parameter configuration](https://github.com/Draegerwerk/SDCcc/?tab=readme-ov-file#test-parameter-configuration) for more information.

```python
import anyio
import toml  # has to be installed by the user

import pysdccc


async def main():
    testparameter_config = {
        'TestParameter': {
            ...
        }
    }
    testparameter_config_path = anyio.Path('/path/to/test_parameter/file.toml')
    await testparameter_config_path.write_text(toml.dumps(testparameter_config))

    runner = pysdccc.SdcccRunner('/path/to/sdccc/result/directory')
    await runner.run(
        config='/path/to/configuration/file.toml',
        requirements='/path/to/requirements/file.toml',
        testparam=testparameter_config_path,
    )

    # or, if you have already downloaded SDCcc
    testparameter_config = await runner.get_test_parameter()  # load default configuration
    testparameter_config['TestParameter']['Biceps547TimeInterval'] = 10
    # save and run as above
```

### Logging

The SDCcc runner provides a logger called `pysdccc.run` that can be used to log messages during the execution of the tests. Stdout is mapped to logging level `info` and stderr to `error`.
Be aware that no further processing of the SDCcc process output is done. Depending on the format you use you may get duplicated timestamps, etc. Also, it might happen that a java error can stretch over multiple lines, which may result in multiple log messages in python for the same java error.

### Execute SDCcc from command-line interface (cli)

There exists a cli wrapper for the SDCcc executable. If `pysdccc[cli]` is installed, `sdccc` can be used to execute arbitrary SDCcc commands, e.g. `sdccc --version`. More information can be found [here](https://github.com/draegerwerk/sdccc?tab=readme-ov-file#running-sdccc).

## Notices

`pysdccc` is not intended for use in medical products, clinical trials, clinical studies, or in clinical routine.

### ISO 9001

`pysdccc` was not developed according to ISO 9001.

## License

[MIT](https://choosealicense.com/licenses/mit/)
