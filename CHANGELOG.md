# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added `CODE_OF_CONDUCT.md` and linked it from contributor-facing project
  documentation.

### Changed
- Disabled pip caching for release workflow install smoke tests so checks install the
  freshly built package artifact.

## [1.1.6] - 2026-04-20

### Added
- Added project governance and support files: `LICENSE`, `CONTRIBUTING.md`,
  `SECURITY.md`, `CHANGELOG.md`, `.editorconfig`, GitHub issue templates, and
  a pull request template.
- Added project metadata links for source, issue reporting, changelog, and
  community documentation.
- Added the PEP 561 `py.typed` marker so type information is exposed to
  consumers.

### Changed
- Updated package metadata and public version reporting to `1.1.6`.
- Expanded README project metadata and community contribution references.

## [1.1.5] - 2026-04-20

### Added
- Added strongly typed METAR and TAF report models with convenience wrappers for
  decoding reports.
- Added expanded parser support for icing forecasts, turbulence forecasts, sea
  conditions, wind shear, runway state groups, trend groups, and complex remarks.
- Added shared METAR and TAF validators with structured validation warnings.
- Added expanded constants and glossary mappings for report types, station
  modifiers, runway values, cloud/weather codes, and remark labels.
- Added `src/weather_decoder/__main__.py` and common CLI helpers for package
  entry-point execution.
- Added a reorganized pytest suite covering decoders, parsers, remarks,
  formatters, models, utilities, and validation behavior.
- Added Dependabot and dependency review configuration.

### Changed
- BREAKING: Dropped Python 3.8 support; the minimum supported Python version is
  now 3.9.
- BREAKING: Enforced stricter METAR and TAF standards compliance, which may
  reject or warn on malformed reports that were previously accepted.
- Migrated the package to a `src/` layout and modernized setuptools
  configuration.
- Reworked decoder internals around token streams, dedicated parser modules,
  structured report models, shared formatters, and validator modules.
- Reorganized METAR formatter output into stable, token-aware sections.
- Modernized GitHub Actions workflows, release automation, dependency handling,
  coverage configuration, Ruff configuration, and mypy configuration.
- Updated CLI behavior and documentation for structured output and improved
  error handling.
- Reformatted decoder modules and tests for consistency.

### Fixed
- Fixed decoding for official METAR and TAF edge cases.
- Fixed complex METAR remark parsing, including corrected reports (`COR`),
  FMH-1 remark labels, runway braking remarks, variable ceiling output, and
  additional remark edge cases.
- Fixed time parsing around month/year rollovers.
- Fixed zero-visibility parsing and wind shear group matching.
- Fixed recent weather, sea condition, icing forecast, turbulence forecast, and
  validation warning output in formatted reports.

## [1.1.4] - 2025-11-29

### Changed
- Updated package and CLI version reporting through `1.1.4`.
- Standardized wind-shift remark keys between the remarks parser and METAR
  formatter.
- Updated `MultiTokenParser.parse_with_lookahead` type hints for Python 3.8
  compatibility.

### Fixed
- Improved past weather event parsing to support both two-digit and four-digit
  time formats.

## [1.1.3] - 2025-11-29

### Changed
- Updated package and CLI version reporting for the next patch release.

### Notes
- The `v1.1.3` tag contains a version metadata-only change and no functional
  decoder changes.

## [1.1.2] - 2025-11-29

### Added
- Added constants for cloud types, lightning frequency, and runway state
  reporting.
- Added broader weather phenomenon and cloud-type pattern support.
- Added dedicated parser modules for remarks, wind, visibility, weather, and
  related METAR/TAF groups.

### Changed
- Refactored METAR and TAF parsing into a more modular parser architecture.
- Consolidated formatting helpers, constants, and utility functions.
- Removed trailing whitespace across the codebase.

## [1.1.1] - 2025-11-29

### Changed
- Updated package and CLI version reporting to `1.1.1`.

## [1.1.0] - 2025-11-29

### Changed
- Updated package and CLI version reporting to `1.1.0`.

## [1.0.9] - 2025-11-29

### Added
- Added support for minimum visibility formatting.

### Changed
- Improved METAR past weather event parsing.
- Refactored sky and weather parsers to handle trend indicators more reliably.
- Updated package metadata to `1.0.9`.

## [1.0.8] - 2025-11-28

### Added
- Added METAR support for `NIL` reports and maintenance indicators.
- Added METAR remark support for altimeter settings.
- Added cloud type parsing for Japanese and Canadian formats.

### Changed
- Migrated packaging configuration from `setup.py` toward `pyproject.toml`.
- Improved runway state reporting.
- Improved visibility and wind parser data handling.
- Streamlined imports, whitespace, CLI argument descriptions, and package
  exports.
- Updated package metadata to `1.0.8`.

### Fixed
- Improved handling of unknown cloud heights across parsers and formatters.

### Notes
- Git history includes a package version `1.0.8` commit, but no `v1.0.8` tag.

## [1.0.7] - 2025-09-15

### Added
- Added METAR support for 24-hour temperature extremes.

### Changed
- Updated package and CLI version reporting to `1.0.7`.

## [1.0.6] - 2025-09-12

### Changed
- Updated package and CLI version reporting through `1.0.6`.
- Upgraded the mypy dependency in pre-commit configuration.

## [1.0.5] - 2025-09-12

### Added
- Added METAR remarks decoding for variable visibility, past weather events,
  and precipitation amount.

### Changed
- Removed the remarks section before decoding the main METAR body so parsed
  fields are not polluted by remark tokens.

## [1.0.4] - 2025-09-11

### Changed
- Updated package and CLI version reporting through `1.0.4`.
- Upgraded the mypy dependency in pre-commit configuration.
- Enhanced GitHub Actions permissions for the release workflow.

## [1.0.3] - 2025-09-11

### Notes
- The `v1.0.3` tag points to the same commit as `v1.0.2`; no additional code
  changes were captured under this tag in Git history.

## [1.0.2] - 2025-09-11

### Changed
- Updated package and CLI version reporting through `1.0.2`.
- Upgraded the mypy dependency in pre-commit configuration.

### Notes
- Git history contains both `1.0.2` and `v1.0.2` tags for this commit.

## [1.0.1] - 2025-09-11

### Fixed
- Added an explicit shell specification for pip installation in the release
  workflow.

## [1.0.0] - 2025-09-11

### Added
- Initial METAR and TAF decoder package with core decoders, parser modules, data
  models, formatting utilities, constants, and CLI entry points.
- Added project build configuration, development requirements, pre-commit
  configuration, README documentation, and GitHub Actions workflows for CI,
  code quality, performance, release, and security checks.

### Changed
- Updated initial CI workflows to use Python 3.12, newer GitHub Actions
  versions, and standardized workflow status output.
- Set Python target support to Python 3.8 and newer in project configuration.

[Unreleased]: https://github.com/6639835/metar-taf-decoder/compare/v1.1.6...HEAD
[1.1.6]: https://github.com/6639835/metar-taf-decoder/compare/v1.1.5...v1.1.6
[1.1.5]: https://github.com/6639835/metar-taf-decoder/compare/v1.1.4...v1.1.5
[1.1.4]: https://github.com/6639835/metar-taf-decoder/compare/v1.1.3...v1.1.4
[1.1.3]: https://github.com/6639835/metar-taf-decoder/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/6639835/metar-taf-decoder/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/6639835/metar-taf-decoder/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/6639835/metar-taf-decoder/compare/v1.0.9...v1.1.0
[1.0.9]: https://github.com/6639835/metar-taf-decoder/compare/0b776b1...v1.0.9
[1.0.8]: https://github.com/6639835/metar-taf-decoder/compare/v1.0.7...0b776b1
[1.0.7]: https://github.com/6639835/metar-taf-decoder/compare/v1.0.6...v1.0.7
[1.0.6]: https://github.com/6639835/metar-taf-decoder/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/6639835/metar-taf-decoder/compare/v1.0.4...v1.0.5
[1.0.4]: https://github.com/6639835/metar-taf-decoder/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/6639835/metar-taf-decoder/releases/tag/v1.0.3
[1.0.2]: https://github.com/6639835/metar-taf-decoder/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/6639835/metar-taf-decoder/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/6639835/metar-taf-decoder/releases/tag/v1.0.0
