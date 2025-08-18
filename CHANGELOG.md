# Changelog

All notable changes to the pysdccc module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-08-18

### Added

- capture logs of the SDCcc subprocess
- added a deprecation warning to all sync functions (except in `_cli.py`)

### Changed

- Remove some of the duplicated code by running async code with anyio
- replaced sync methods of `download` and `is_downloaded` with async functions and added a `_sync` extension to the end of the sync functions
- updated dependencies. most notable is increasing the `junitparser>=4`

## [0.1.0] - 2025-05-16

### Added

- initial code
