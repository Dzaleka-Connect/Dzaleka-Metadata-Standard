# Changelog

All notable changes to the Dzaleka Metadata Standard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-06-20

### Added
- **Schema**: DMS JSON Schema (Draft 2020-12) with 15 fields based on Dublin Core
- **Schema**: YAML version of the schema for human readability
- **Schema**: JSON-LD context for linked data interoperability
- **CLI**: `dms init` — Interactive record creation wizard
- **CLI**: `dms validate` — Single file and batch directory validation
- **CLI**: `dms convert csv2json` — CSV to JSON conversion
- **CLI**: `dms convert json2csv` — JSON to CSV conversion
- **CLI**: `dms info` — Schema version and field summary display
- **Docs**: Field Guide with detailed definitions for all fields
- **Docs**: Best Practices guide for metadata entry
- **Docs**: Getting Started tutorial
- **Examples**: Story (oral history), Photo, Document, Audio, Event records
- **Examples**: Batch CSV import template
- **Tests**: Validation and conversion test suites

### Heritage Item Types
- `story` — Oral histories, personal narratives
- `photo` — Photographs and images
- `document` — Administrative records and reports
- `audio` — Sound recordings and music
- `video` — Video recordings
- `event` — Community event documentation
- `map` — Spatial representations
- `artwork` — Visual arts and crafts

### Dublin Core Compatibility
- All core fields map to Dublin Core elements and terms
- JSON-LD context enables linked data publishing
- Compatible with existing Dublin Core workflows
