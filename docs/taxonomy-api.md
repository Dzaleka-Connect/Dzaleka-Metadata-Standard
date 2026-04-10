# DMS Taxonomy API

> Query DMS vocabularies as full schemes, filtered term sets, deprecated lists, structure summaries, change logs, and semantic-web serializations.

---

## Overview

When the local web server is running:

```bash
dms web --port 8080
```

the vocabulary service is available under:

```text
http://127.0.0.1:8080/api/taxonomy
```

The service is designed for DMS-native vocabularies such as:

- `types`
- `roles`
- `access_levels`
- `relation_types`
- `consent_statuses`
- `sensitivity_markers`

---

## Endpoints

### List available vocabularies

```http
GET /api/taxonomy
```

### Retrieve a full vocabulary

```http
GET /api/taxonomy/types
```

### Retrieve a filtered subset of terms

```http
GET /api/taxonomy/types/terms?ids=story,photo
GET /api/taxonomy/types/terms?q=recording
GET /api/taxonomy/types?include_deprecated=true
```

Supported query parameters:

- `ids` — comma-separated term IDs or short IDs
- `q` — case-insensitive search across label, definition, and ID
- `include_deprecated=true` — include deprecated terms in results
- `limit` — maximum number of returned terms
- `offset` — result offset for paging

### Retrieve one term

```http
GET /api/taxonomy/types/story
GET /api/taxonomy/types/terms/story
```

### Retrieve deprecated terms

```http
GET /api/taxonomy/types/deprecated
```

### Retrieve a vocabulary change log

```http
GET /api/taxonomy/types/changes
GET /api/taxonomy/types/changes?term=image
```

### Retrieve vocabulary structure metadata

```http
GET /api/taxonomy/types/structure
```

This returns a summary such as:

- whether the vocabulary is flat or hierarchical
- active term count
- deprecated term count
- supported output formats

---

## Output Formats

Vocabulary documents and term subsets support:

- `json`
- `jsonld`
- `ttl`
- `rdfxml`

Single-term lookups additionally support:

- `html`

Use either the `format` query parameter or the `Accept` header.

Examples:

```http
GET /api/taxonomy/types?format=jsonld
GET /api/taxonomy/types?format=ttl
GET /api/taxonomy/types?format=rdfxml
GET /api/taxonomy/types/story?format=html
```

Equivalent `Accept` headers:

- `application/ld+json`
- `text/turtle`
- `application/rdf+xml`
- `text/html`

---

## Notes

- `types` currently has a curated taxonomy file in `dms/data/taxonomy/types.json`.
- Other DMS vocabularies are generated from the active schema when a dedicated taxonomy file does not yet exist.
- The semantic formats are intended for linked-data publishing and integration, while the JSON and HTML responses are the easiest formats for contributor tooling.
