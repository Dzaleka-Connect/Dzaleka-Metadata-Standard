# Dzaleka Metadata Standard (DMS)

[![License: MIT](https://img.shields.io/badge/Code-MIT-blue.svg)](LICENSE)
[![License: CC BY 4.0](https://img.shields.io/badge/Docs-CC%20BY%204.0-lightgrey.svg)](LICENSE-DOCS)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://www.python.org/)
[![Schema: v1.1.0](https://img.shields.io/badge/Schema-v1.1.0-orange.svg)](dms/data/schema/dms.json)

> **An open-source metadata specification and toolkit for describing, organising, and sharing digital heritage content from Dzaleka Refugee Camp.**

---

## What is DMS?

The **Dzaleka Metadata Standard (DMS)** is an open-source metadata specification and toolkit designed to describe, organise, and share digital heritage content from [Dzaleka Refugee Camp](https://en.wikipedia.org/wiki/Dzaleka_refugee_camp) in Malawi.

It provides a standardised, interoperable, and reusable schema for heritage items such as stories, photos, documents, audio, and events.

## 🧭 Purpose

The purpose of DMS is to:

- **Enable consistent metadata creation** for heritage assets
- **Support discoverability, interoperability, and reuse** of heritage data
- **Provide tools to validate, manage, and export** metadata
- **Serve as an open standard** for heritage documentation

DMS helps both technical systems and community contributors work with heritage content in a structured way.

## 📦 What DMS Includes

### 📌 Metadata Schema

A machine-readable specification defining fields, types, and constraints for heritage metadata.

Available formats:
- **JSON Schema** — [`dms/data/schema/dms.json`](dms/data/schema/dms.json) (Draft 2020-12)
- **YAML Schema** — [`dms/data/schema/dms.yaml`](dms/data/schema/dms.yaml)
- **JSON-LD / RDF** — [`dms/data/schema/dms.jsonld`](dms/data/schema/dms.jsonld) for semantic web / linked data use

### 🛠️ Python Tools & Web UI

A suite of tools for creating, validating, and converting metadata records. Includes both a command-line interface (CLI) and a local premium Web UI (DMS Vault). See [Quick Start](#quick-start) below.

### 📖 Documentation

Field definitions, best practices, and tutorials for metadata entry. See [Documentation](#documentation).

### 📁 Example Records

Sample records covering stories, photos, documents, audio, and events. See [Examples](#examples).

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Dzaleka-Connect/Dzaleka-Metadata-Standard.git
cd dzaleka-metadata-standard

# Install the CLI tools
pip install -e .
```

### The Web UI (DMS Vault)

The easiest way to build, validate, and manage records is using the built-in local Web UI:

```bash
dms web --port 8080 --dir records/
```

### Create a Record via CLI

```bash
# Interactive wizard
dms init

# Skip type selection prompt
dms init --type poem

# Save to specific file
dms init --output my-record.json
```

### Validate a Record

```bash
# Single file
dms validate examples/story.json

# All files in a directory
dms validate --dir examples/
```

### Search & Analyze

```bash
# Search records by type, subject, or free-text
dms search --dir records/ --type poem -q "displacement"

# View collection analytics (types, languages, completion)
dms stats --dir records/

# Generate a browsable HTML catalogue of your collection
dms report --dir records/ --output catalogue.html
```

### Interoperability Tools

```bash
# Export record(s) as JSON-LD for semantic web
dms export examples/story.json

# Convert CSV batch to JSON records
dms convert csv2json examples/batch.csv

# Compare two records field-by-field
dms diff record_v1.json record_v2.json
```

### View Schema Info

```bash
dms info
```

## Schema Overview

A DMS record describes a single heritage item with these fields:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | ✅ | Unique identifier (UUID) |
| `title` | ✅ | Name of the item |
| `type` | ✅ | Category: `story`, `photo`, `document`, `audio`, `video`, `event`, `map`, `artwork`, `site`, `poem` |
| `description` | ✅ | Narrative context |
| `language` | ✅ | Language code (BCP 47) |
| `creator` | Recommended | Who created it (name, role, affiliation) |
| `date` | Recommended | When it was created or occurred |
| `subject` | Recommended | Controlled tags and keywords |
| `subject_ref` | Optional | Structured subject identifiers and scheme references |
| `location` | Recommended | Place name, area, coordinates |
| `rights` | Recommended | License, access level, holder |
| `source` | Optional | Contributor, collection, original format |
| `format` | Optional | MIME type of the digital object |
| `technical` | Optional | File-level technical metadata |
| `relation` | Optional | IDs of related records |
| `relation_detail` | Optional | Typed relationships to related records or resources |
| `coverage` | Optional | Time period covered |

All fields map to [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) for broad interoperability, with Dzaleka-specific extensions for camp areas and access levels.

## Repository Structure

```
├── dms/                 Python CLI tools
│   ├── cli.py           Command entry points
│   ├── validator.py     Schema validation engine
│   ├── generator.py     Interactive record creator
│   └── converter.py     CSV ↔ JSON converter
│
│   data/schema/         Schema definitions
│   ├── dms.json         JSON Schema (Draft 2020-12)
│   ├── dms.yaml         YAML version
│   └── dms.jsonld       JSON-LD context for linked data
│
├── docs/                Documentation
│   ├── field-guide.md   Field definitions & guidelines
│   ├── best-practices.md Metadata entry best practices
│   ├── semantic-tagging.md Controlled vocabularies and richer subject metadata
│   └── getting-started.md Installation & tutorial
│
├── examples/            Sample records
│   ├── story.json       Oral history
│   ├── photo.json       Photograph
│   ├── document.json    Administrative record
│   ├── audio.json       Music recording
│   ├── event.json       Community event
│   ├── site.json        Heritage site (Site Register)
│   ├── mural.json       Public artwork (Art Catalogue)
│   ├── poem.json        Poetry
│   └── batch.csv        CSV batch import example
│
└── tests/               Test suite
```

## Examples

The [`examples/`](examples/) directory contains sample records for common heritage item types:

- **[story.json](examples/story.json)** — "Journey to Dzaleka: A Story of Hope" (oral history)
- **[photo.json](examples/photo.json)** — "Market Day at Dzaleka" (daily life photography)
- **[document.json](examples/document.json)** — "Community School Registration Records, 2018"
- **[audio.json](examples/audio.json)** — "Traditional Songs of the Great Lakes Region"
- **[event.json](examples/event.json)** — "World Refugee Day Celebration 2024"
- **[site.json](examples/site.json)** — "Dzaleka Health Centre" (from [Site Register](https://services.dzaleka.com/site-register/))
- **[mural.json](examples/mural.json)** — "Child Early Marriage Awareness Mural" (from [Art Catalogue](https://services.dzaleka.com/public-art-catalogue/))
- **[poem.json](examples/poem.json)** — "Home Is a Word I Carry" (poetry)
- **[batch.csv](examples/batch.csv)** — Records in CSV format for batch import

## Documentation

- **[Field Guide](docs/field-guide.md)** — Detailed definitions for every schema field
- **[Best Practices](docs/best-practices.md)** — Guidelines for quality metadata entry
- **[Semantic Tagging](docs/semantic-tagging.md)** — AP-inspired guidance for controlled vocabularies and richer subject metadata
- **[Getting Started](docs/getting-started.md)** — Installation and first steps tutorial

## Interoperability

DMS is designed to work with existing standards and systems. The [`dms.jsonld`](dms/data/schema/dms.jsonld) context enables linked data publishing with mappings to:

| Vocabulary | Prefix | Used for |
|-----------|--------|----------|
| [Dublin Core](https://www.dublincore.org/) | `dc:`, `dcterms:` | Core metadata fields (title, creator, subject, rights, etc.) |
| [FOAF](https://xmlns.com/foaf/spec/) | `foaf:` | Person/Agent descriptions (`foaf:name`, `foaf:Person`, `foaf:Image`) |
| [BIBO](https://www.dublincore.org/specifications/bibo/) | `bibo:` | Bibliographic roles (`bibo:editor`, `bibo:translator`, `bibo:interviewer`) |
| [Schema.org](https://schema.org/) | `schema:` | Creative works, places, events, affiliations |
| [W3C Geo](https://www.w3.org/2003/01/geo/) | `geo:` | Geographic coordinates (`geo:lat`, `geo:long`) |
| [SKOS](https://www.w3.org/2004/02/skos/) | `skos:` | Subject vocabularies and concept schemes |

**Additional format support:**
- **CSV** — Import/export for spreadsheet-based workflows
- **JSON Schema** — Machine-readable validation for any language or platform

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Areas where you can help:

- 📝 Adding example records from the Dzaleka community
- 🌐 Translating documentation into Swahili, French, or Kinyarwanda
- 🔧 Improving the CLI tools
- 📖 Writing guides for specific use cases
- 🐛 Reporting bugs and suggesting improvements

## License

- **Code** (Python tools): [MIT License](LICENSE)
- **Schema & Documentation**: [Creative Commons Attribution 4.0](LICENSE-DOCS)

## Acknowledgments

- The **Dzaleka refugee community** for their heritage, stories, and resilience
- [Dublin Core Metadata Initiative](https://www.dublincore.org/) for the foundational metadata standard
- All contributors and volunteers who help preserve Dzaleka's digital heritage

---

<p align="center">
  <em>Preserving heritage. Empowering community. Building the future.</em>
</p>
