# Changelog

All notable changes to this project are documented in this file.

## [0.1.2] - 2026-02-22

### Highlights
- Major README overhaul with clearer, step-by-step documentation.
- Template/layout documentation consolidated and improved.
- Expanded class-based view documentation with practical HTML + API examples.
- Expanded OAuth/OIDC and custom login provider documentation.
- Expanded database/migration documentation with full workflows.
- i18n documentation now includes full Babel workflow (`extract`, `init`, `update`, `compile`).
- Custom login providers can now be resolved from the app first, with FlaskSpark fallback.

### Changed
- Login provider loading now checks modules in this order:
  1. `<app_module>.helpers.login_provider_<name>`
  2. `flaskspark.helpers.login_provider_<name>`
- Project version bumped to `0.1.2` in `pyproject.toml`.

### Documentation
- Added/updated guidance for:
  - quick start and configuration precedence
  - templates and framework hook blocks
  - assets and bundle behavior
  - class-based views and API method patterns
  - OAuth/OIDC setup and login-provider behavior
  - database migrations and model lifecycle
  - i18n setup and compile process
- Clarified current provider status:
  - `OAuth` is implemented
  - `Default` is currently a stub (not fully implemented yet)

### Notes
- No breaking API changes intended in this release.
- Existing apps should continue to work; custom login provider setups can now live in the app package directly.
