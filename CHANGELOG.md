# Changelog

All notable changes to the Dzaleka Metadata Standard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-04-10

### Changed
- **Schema**: Clarified `subject` as a controlled-vocabulary field in the JSON and YAML schema descriptions
- **Schema**: Upgraded schema version to `1.1.0`
- **JSON-LD**: Cleaned up object mappings for `license`, `collection`, `relation`, and nested metadata objects

### Added
- **Schema**: Optional `subject_ref`, `technical`, and `relation_detail` fields for authority IDs, file metadata, and typed relationships
- **Schema**: Optional consent/sensitivity metadata under `rights`, plus creator, place, and collection identifiers
- **CLI**: Interactive generator prompts for structured subject references, technical metadata, consent/sensitivity, and typed relations
- **CLI**: CSV conversion support for new v1.1 fields
- **API**: Local taxonomy service for vocabularies, subsets, deprecated terms, change logs, structure summaries, and JSON-LD/Turtle/RDF/XML output
- **Web UI**: Dedicated Vocabulary workspace for browsing DMS term sets, inspecting term history, and attaching structured subject references to active records
- **Docs**: Semantic Tagging guide with DMS-native recommendations for building a community-managed taxonomy
- **Docs**: Semantic Tagging guide now covers authorities, stable identifiers, deprecations, mappings, and relevance-aware future tooling
- **Docs**: Semantic Tagging guide now includes SKOS labels/matches, change notes, and geography/organization/person relationship modeling
- **Docs**: Taxonomy API guide for local vocabulary endpoints and semantic-web formats
- **Docs**: Stronger guidance in the Field Guide and Best Practices on canonical subject terms and tag governance
- **Examples**: Refreshed story and fixture examples showing v1.1 structured metadata patterns

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
