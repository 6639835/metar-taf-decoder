# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project governance files: `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, and `CHANGELOG.md`.
- GitHub issue templates and pull request template.
- `.editorconfig` for consistent cross-editor formatting.
- PEP 561 `py.typed` marker so type information is exposed to consumers.

## [1.1.4] - 2025-04-20

### Changed
- Dropped support for Python 3.8; minimum supported version is now 3.9.
- Reformatted decoder modules and tests for consistency.

### Fixed
- Improved decoding of complex remarks and `COR` METAR reports.
- Handled additional remarks parsing edge cases.
- Resolved parser issues with several official METAR and TAF edge cases.

[Unreleased]: https://github.com/6639835/metar-taf-decoder/compare/v1.1.4...HEAD
[1.1.4]: https://github.com/6639835/metar-taf-decoder/releases/tag/v1.1.4
