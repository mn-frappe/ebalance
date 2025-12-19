## [1.5.0](https://github.com/mn-frappe/ebalance/compare/v1.4.1...v1.5.0) (2025-12-19)

### 🚀 Features

* Add optional eBarimt VAT reconciliation integration ([#5](https://github.com/mn-frappe/ebalance/issues/5)) ([9b5bd3a](https://github.com/mn-frappe/ebalance/commit/9b5bd3ac075208dcce0929ec0db930dbbd1dc2b9))

## [1.4.1](https://github.com/mn-frappe/ebalance/compare/v1.4.0...v1.4.1) (2025-12-18)

### 🐛 Bug Fixes

* update linter workflow to match passing pattern ([251124c](https://github.com/mn-frappe/ebalance/commit/251124c6e73ce5a5e57dc7d2ea439097f34eba62))

## [1.4.0](https://github.com/mn-frappe/ebalance/compare/v1.3.0...v1.4.0) (2025-12-17)

### 🚀 Features

* add CodeQL, CODEOWNERS, MkDocs documentation ([1891b59](https://github.com/mn-frappe/ebalance/commit/1891b5965fa7d99bdbc10121cc9ca9e1989ab75c))
* add mypy type checking, matrix testing, enhanced VS Code ([2050a04](https://github.com/mn-frappe/ebalance/commit/2050a0411ac90d9b3112c3e327cd34caed7e85ab))
* add semantic-release for automatic versioning ([b0ee3a3](https://github.com/mn-frappe/ebalance/commit/b0ee3a3151a78c9fbf51f29fb5054f24f168b812))
* add telemetry for GitHub issue auto-creation ([2683524](https://github.com/mn-frappe/ebalance/commit/268352483b49fc059fcf4157a22b59029c259cba))

### 🐛 Bug Fixes

* resolve type errors in telemetry module ([914bf5c](https://github.com/mn-frappe/ebalance/commit/914bf5ce04583405d553c23d41ac480cc5b88d03))
* semantic-release auth and missing npm package ([5fe7a98](https://github.com/mn-frappe/ebalance/commit/5fe7a981d43d0e2111cf6c8a5682f984d89c731d))

# Changelog

All notable changes to eBalance will be documented in this file.

## [1.3.0] - 2024-12-17

### Added
- Multi-company entity support
- Test Connection button in settings
- Comprehensive test suite (46 tests)
- Enhanced ERPNext app compatibility

### Changed
- All sections collapsible by default
- Improved workspace layout
- Updated documentation for mn_chart.csv compliance

### Fixed
- Duplicate pyproject.toml sections
- Bootinfo cache clearing after workspace changes

## [1.2.0] - 2024-12-17

### Added
- Multi-company entity support
- Enhanced ERPNext app compatibility
- Local mn_entity.py for CI compatibility

## [1.1.1] - 2024-12-16

### Added
- 100% MOF API integration
- Performance optimizations
- Connection pooling
- Response caching

### Changed
- Improved API error handling
- Better field descriptions

## [1.1.0] - 2024-12-16

### Added
- Mongolian field descriptions
- Collapsible sections
- eBalance workspace integration
- i18n support with Mongolian translations

## [1.0.0] - 2024-12-16

### Added
- Initial release
- MOF eBalance API integration
- Chart of Accounts mapping (mn_chart.csv)
- Financial statement generation
- Balance sheet and P&L reports
- Trial balance integration
