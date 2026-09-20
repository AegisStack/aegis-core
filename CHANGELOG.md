# Changelog

All notable changes to Aegis SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- TBD

### Changed
- TBD

### Fixed
- Corrected the `[0.1.0]` entry's frontend test count (was overstated as 24; actual count was 15).
- Fixed onboarding docs (`README.md`, `docs/QUICKSTART.md`, `docs/SDK_GUIDE.md`, `docs/RUNNING_LOCALLY.md`, `docs/RELEASING.md`) referencing a `wrap_tool` function that never existed in the public API; examples now use the real `aegis.wrap()`/`aegis.wrap_function_map()`.

## [0.1.0] - 2026-04-06

### Added
- **Core SDK features:**
  - Policy engine with YAML-based policy definitions
  - 8 condition operators: `eq`, `neq`, `lt`, `lte`, `gt`, `gte`, `in`, `not_in`, `regex`
  - Tool wrapper with function signature preservation using `functools.update_wrapper`
  - Configurable on_deny behaviors: `raise`, `return_error`, `silent`
  - Escalation manager for human-in-the-loop workflows
  - Audit logging with structured observability events
  - File sink for audit records (JSONL format)

- **Dashboard Platform:**
  - FastAPI backend with JWT authentication
  - PostgreSQL + TimescaleDB for time-series audit data
  - Real-time WebSocket feed for live monitoring
  - Next.js 14 frontend with React Query
  - Policy editor with YAML validation
  - Audit trail with filtering and search
  - Metrics dashboard with Recharts visualizations
  - Alert management system
  - Role-based access control (viewer, operator, admin)

- **Testing:**
  - 44 SDK unit tests with pytest
  - 15 frontend component tests with Jest
  - 13 backend API tests with async fixtures
  - Complete test coverage for all core modules

- **Documentation:**
  - README with quick start guide
  - QUICKSTART.md for local setup
  - SDK_GUIDE.md with complete API reference
  - DASHBOARD_SUMMARY.md with architecture details
  - TEST_RESULTS.md with test execution summary
  - RELEASING.md with publishing guide

- **Examples:**
  - Basic policy enforcement example
  - Multi-tool wrapping example
  - Escalation workflow example

### Technical Details
- **SDK:** 4,475 lines of production code
- **Dashboard:** 3,500+ lines (backend + frontend)
- **Dependencies:** Python 3.10+, FastAPI, SQLAlchemy, Pydantic v2
- **Frontend:** Next.js 14, React 18, TailwindCSS, React Query
- **Database:** PostgreSQL 15 with TimescaleDB extension
- **Deployment:** Docker Compose with multi-container setup

### Breaking Changes
- None (initial release)

---

## Version Naming

- **[0.1.0]** - Initial MVP release with core features
- **[0.2.0]** - (Planned) Additional condition operators, performance improvements
- **[1.0.0]** - (Planned) Production-ready with stable API

[Unreleased]: https://github.com/yourorg/aegis-core/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourorg/aegis-core/releases/tag/v0.1.0
