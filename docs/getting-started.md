# Getting Started with DMS

> Step-by-step guide to installing the DMS tools and creating your first metadata record.

---

## Prerequisites

- **Python 3.9 or newer** — Check with `python3 --version`
- **pip** — Python package manager (usually included with Python)
- **Git** — For cloning the repository

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Dzaleka-Connect/Dzaleka-Metadata-Standard.git
cd dzaleka-metadata-standard
```

### 2. Install the CLI Tools

```bash
# Install in development mode (recommended)
pip install -e .

# Or install normally
pip install .
```

### 3. Verify the Installation

```bash
dms --version
dms info
```

You should see the DMS version and a table of schema fields.

---

## Creating Your First Record

### The Built-in Web UI (Recommended)

The easiest, most robust way to create and manage records is using the local DMS Vault web interface:

```bash
dms web --port 8080 --dir records/
```

This launches a premium, dark-themed local web app at `http://localhost:8080` where you can:
- Fill out metadata fields via a beautiful, structured GUI
- Get live validation feedback against the schema
- Add multi-value creators and subject tags effortlessly
- Copy and export raw JSON or JSON-LD

The CLI wizard now also supports richer v1.1 fields such as structured subject references,
technical metadata, consent/sensitivity metadata, and typed relations.

### Terminal / Interactive Mode

For command-line users, you can run the interactive wizard:

```bash
# General wizard
dms init

# Skip the type selection prompt
dms init --type story

# Save directly to a specific file
dms init --output records/my-story.json
```

### From a Template

You can also copy and modify one of the [example records](../examples/):

```bash
cp examples/story.json my-record.json
# Edit my-record.json with your favorite text editor
```

Remember to generate a new `id` (UUID) for each new record!

---

## Validating Records

### Single File

```bash
dms validate my-record.json
```

If the record is valid, you'll see a green checkmark. If there are errors, the tool will show a detailed table explaining what needs to be fixed.

### Entire Directory

```bash
dms validate --dir records/
```

This validates every `.json` file in the directory and shows a summary.

### Understanding Validation Output

**Valid record:**
```
╭────────────────────────────────────╮
│ ✓ VALID  examples/story.json       │
╰────────────────────────────────────╯
  ⚠ Recommended field 'Format' is not provided.
```

**Invalid record:**
```
╭────────────────────────────────────╮
│ ✗ INVALID  bad-record.json         │
╰────────────────────────────────────╯
 Field            Issue
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Title            Value cannot be empty.
 Type             Invalid value 'unknown'. Allowed: story, ...
```

**Errors** (❌) must be fixed — the record does not conform to the schema.

**Warnings** (⚠) are suggestions — recommended fields that you may want to add.

---

## Managing the Archive

As your archive grows, DMS provides powerful tools to search and manage your collection from the command line.

### Searching Records

Search through all metadata records using combinations of filters or free text:

```bash
# Filter by type and language
dms search --dir records/ --type poem --language sw

# Search by subject tag
dms search --dir records/ --subject "displacement"

# Full text search across title and description
dms search --dir records/ -q "refugee camp" --verbose
```

### Collection Statistics

View analytics about your archive, including top asset types, language distribution, and a heatmap indicating missing recommended fields:

```bash
dms stats --dir records/
```

### Generating a HTML Catalogue

Generate a browsable local HTML interface that you can open locally or host for the community:

```bash
# Generate HTML
dms report --dir records/ --output my_catalogue.html

# Generate Markdown
dms report --dir records/ --format md
```

### Advanced: Diffing & JSON-LD Export

Compare structural changes between two records using the diff tool:

```bash
dms diff old_record.json new_record.json
```

Publish metadata to the wider Semantic Web via JSON-LD (mapping Dzaleka fields to FOAF, BIBO, Dublin Core, and Schema.org):

```bash
# Export single artifact
dms export records/photo.json

# Export an entire directory as an aggregated @graph linked-data payload
dms export --dir records/
```

---

## Working with CSV

### Importing from CSV

If you have metadata in a spreadsheet, export it as CSV and convert:

```bash
dms convert csv2json my-data.csv
```

This creates a JSON file with all records. See [batch.csv](../examples/batch.csv) for the expected column format.

**Multi-value columns** use `|` (pipe) as a separator:
- Creator names: `Alice|Bob`
- Creator identifiers: `dms-person:alice|dms-person:bob`
- Creator roles: `narrator|interviewer`
- Subject tags: `history|culture|music`
- Sensitivity tags: `trauma-sensitive|personal-data`

Additional v1.1 CSV columns support structured identifiers, typed relations, and technical
metadata when you need richer archival description.

### Exporting to CSV

```bash
dms convert json2csv my-record.json --output export.csv
```

### Round-Trip

You can convert back and forth:

```bash
# CSV → JSON
dms convert csv2json data.csv --output data.json

# JSON → CSV
dms convert json2csv data.json --output data-export.csv
```

---

## Project Structure

Once you start building your archive, consider organizing records like this:

```
my-archive/
├── records/
│   ├── stories/
│   │   ├── story_b3e7c8a1.json
│   │   └── story_f4a2b1c3.json
│   ├── photos/
│   │   └── photo_a1f2e3d4.json
│   └── events/
│       └── event_e9f0a1b2.json
├── imports/
│   └── batch-2024-06.csv
└── exports/
    └── all-records.csv
```

---

## Next Steps

- 📖 Read the [Field Guide](field-guide.md) for detailed field definitions
- 📋 Review [Best Practices](best-practices.md) for quality metadata
- 🔗 Explore the [JSON-LD context](../dms/data/schema/dms.jsonld) for linked data integration
- 🤝 See [CONTRIBUTING.md](../CONTRIBUTING.md) to help improve DMS

---

## Troubleshooting

### `dms: command not found`

Make sure you installed with `pip install -e .` and that your Python scripts directory is in your PATH:

```bash
# Check where pip installs scripts
python3 -m site --user-base
# Add the bin directory to your PATH if needed
```

### `FileNotFoundError: DMS schema not found`

Make sure you're running `dms` from within the repository directory, or install the package so the schema path resolves correctly.

### `jsonschema` validation errors you don't understand

Run `dms info` to see all valid field values and types. Check the [Field Guide](field-guide.md) for details on each field.
