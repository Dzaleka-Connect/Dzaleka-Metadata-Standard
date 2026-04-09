# DMS Field Guide

> Detailed definitions, guidelines, and examples for every field in the Dzaleka Metadata Standard.

---

## Required Fields

These fields **must** be present in every DMS record.

---

### `id`

| Property | Value |
|----------|-------|
| **Type** | String (UUID v4) |
| **Required** | ✅ Yes |
| **Dublin Core** | `dc:identifier` |
| **Format** | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |

A universally unique identifier for the record. Generated automatically by `dms init`.

**Example:**
```json
"id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c"
```

---

### `title`

| Property | Value |
|----------|-------|
| **Type** | String (1–500 characters) |
| **Required** | ✅ Yes |
| **Dublin Core** | `dc:title` |

The name or title of the heritage item. Should be descriptive and specific.

**Guidelines:**
- Use the original title if one exists
- Include dates or locations when helpful for disambiguation
- Avoid generic titles like "Photo" or "Document"

**Examples:**
```json
"title": "Journey to Dzaleka: A Story of Hope"
"title": "Market Day at Dzaleka"
"title": "Community School Registration Records, 2018"
```

---

### `type`

| Property | Value |
|----------|-------|
| **Type** | String (enum) |
| **Required** | ✅ Yes |
| **Dublin Core** | `dc:type` |
| **Allowed values** | `story`, `photo`, `document`, `audio`, `video`, `event`, `map`, `artwork`, `site`, `poem` |

The category of the heritage item.

| Value | Use for |
|-------|---------|
| `story` | Oral histories, personal narratives, written accounts |
| `photo` | Photographs, images |
| `document` | Administrative records, reports, letters, certificates |
| `audio` | Sound recordings, music, interviews |
| `video` | Video recordings, films |
| `event` | Documentation of community events and gatherings |
| `map` | Maps, spatial representations of the camp |
| `artwork` | Paintings, murals, drawings, crafts, sculptures, installations |
| `site` | Cultural, historical, or community locations and landmarks |
| `poem` | Poetry, spoken word, and literary works |

---

### `description`

| Property | Value |
|----------|-------|
| **Type** | String (minimum 1 character) |
| **Required** | ✅ Yes |
| **Dublin Core** | `dc:description` |

A narrative summary providing context about the heritage item. This is one of the most important fields for discoverability.

**Guidelines:**
- Explain what the item is and why it matters
- Include relevant historical or cultural context
- Mention people, places, or events featured
- Write in the language specified by the `language` field

**Example:**
```json
"description": "An oral history account of a Congolese family's journey from Bukavu to Dzaleka Refugee Camp in 2015. The narrator describes the challenges of displacement, the experience of crossing borders, and the sense of community found upon arrival."
```

---

### `language`

| Property | Value |
|----------|-------|
| **Type** | String (IETF BCP 47 code) |
| **Required** | ✅ Yes |
| **Dublin Core** | `dc:language` |
| **Pattern** | `^[a-z]{2,3}(-[A-Z]{2,4})?$` |

The primary language of the content.

| Code | Language |
|------|----------|
| `en` | English |
| `sw` | Swahili |
| `fr` | French |
| `rw` | Kinyarwanda |
| `ki` | Kirundi |
| `ln` | Lingala |
| `so` | Somali |
| `ny` | Chichewa |

---

## Recommended Fields

These fields are **strongly recommended** for complete records.

---

### `creator`

| Property | Value |
|----------|-------|
| **Type** | Array of Creator objects |
| **Required** | Recommended |
| **Dublin Core** | `dc:creator` |

The person(s) or organization(s) who created the heritage item.

**Creator object properties:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | String | Yes | Full name |
| `identifier` | String | No | Stable local identifier or URI for the creator |
| `role` | Enum | No | Role in creating the item |
| `affiliation` | String | No | Organization or community |

**Valid roles:** `author`, `photographer`, `interviewer`, `interviewee`, `narrator`, `artist`, `muralist`, `sculptor`, `poet`, `curator`, `recorder`, `editor`, `translator`, `organizer`, `contributor`

**Example:**
```json
"creator": [
  {
    "name": "Marie Consolée",
    "role": "narrator"
  },
  {
    "name": "Jean-Baptiste Mushimiyimana",
    "role": "interviewer",
    "affiliation": "Dzaleka Digital Heritage Project"
  }
]
```

---

### `date`

| Property | Value |
|----------|-------|
| **Type** | DateInfo object |
| **Required** | Recommended |
| **Dublin Core** | `dc:date`, `dcterms:created`, `dcterms:modified` |

Date information associated with the item. All dates use ISO 8601 format (`YYYY-MM-DD`).

| Field | Description |
|-------|-------------|
| `created` | When the metadata record was created |
| `modified` | When the record was last modified |
| `event_date` | When the original heritage item was created or occurred |

**Example:**
```json
"date": {
  "created": "2024-03-15",
  "event_date": "2015-08-22"
}
```

---

### `subject`

| Property | Value |
|----------|-------|
| **Type** | Array of strings (unique) |
| **Required** | Recommended |
| **Dublin Core** | `dc:subject` |

Tags or keywords describing the content. Treat this as a lightweight controlled-vocabulary
field whenever possible: use shared, canonical terms so related records can be grouped
and found consistently.

**Guidelines:**
- Use lowercase for consistency
- Prefer terms from a shared local vocabulary or taxonomy
- Include both broad and specific terms
- Use one canonical label per concept across the collection
- Add cultural or community-specific terms where appropriate
- Mix facets such as format, theme, place, people, and time
- Aim for 3–10 tags per record

**Example:**
```json
"subject": ["oral history", "displacement", "Congo", "journey", "resilience"]
```

For a more structured tagging approach inspired by newsroom metadata systems, see
[Semantic Tagging](semantic-tagging.md).

---

### `subject_ref`

| Property | Value |
|----------|-------|
| **Type** | Array of ConceptReference objects |
| **Required** | Optional |
| **Dublin Core / SKOS** | `dc:subject`, `skos:prefLabel` |

Structured references for subject concepts. Use this when you want to keep stable
local identifiers or link a record to a named taxonomy scheme without replacing the
simple `subject` tags.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `identifier` | String | Yes | Stable local identifier or URI for the concept |
| `label` | String | No | Preferred human-readable label |
| `scheme` | String | No | Name of the taxonomy or concept scheme |

**Example:**
```json
"subject_ref": [
  {
    "identifier": "dms-subject:oral-history",
    "label": "oral history",
    "scheme": "DMS Subject Taxonomy"
  }
]
```

---

### `location`

| Property | Value |
|----------|-------|
| **Type** | Location object |
| **Required** | Recommended |
| **Dublin Core** | `dcterms:spatial` |

Geographic information associated with the item.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | String | Yes | Human-readable place name |
| `identifier` | String | No | Stable local identifier or URI for the place |
| `area` | String | No | Specific area/section within the location |
| `latitude` | Number | No | Latitude (-90 to 90) |
| `longitude` | Number | No | Longitude (-180 to 180) |

The `area` field is a **Dzaleka-specific extension** for identifying camp sections (e.g., "Section A", "Market Area", "Community Center").

**Example:**
```json
"location": {
  "name": "Dzaleka Refugee Camp",
  "area": "Community Center",
  "latitude": -13.7833,
  "longitude": 33.9833
}
```

---

### `rights`

| Property | Value |
|----------|-------|
| **Type** | Rights object |
| **Required** | Recommended |
| **Dublin Core** | `dc:rights` |

Licensing and access information.

| Field | Type | Description |
|-------|------|-------------|
| `license` | String | SPDX license identifier (e.g., `CC-BY-4.0`) |
| `access_level` | Enum | `public`, `restricted`, or `community-only` |
| `consent_status` | Enum | `obtained`, `pending`, `not-required`, `unknown`, or `withheld` |
| `sensitivity` | Array | Sensitivity markers such as `personal-data` or `trauma-sensitive` |
| `access_note` | String | Context explaining restrictions or safe-use guidance |
| `holder` | String | Name of the rights holder |

**Access levels:**

| Level | Meaning |
|-------|---------|
| `public` | Open to everyone |
| `restricted` | Requires permission to access |
| `community-only` | Available only to Dzaleka community members |

**Example:**
```json
"rights": {
  "license": "CC-BY-NC-4.0",
  "access_level": "public",
  "consent_status": "obtained",
  "sensitivity": ["trauma-sensitive"],
  "access_note": "Narrator approved public sharing of the transcription.",
  "holder": "Marie Consolée"
}
```

---

## Optional Fields

---

### `source`

| Property | Value |
|----------|-------|
| **Type** | Source object |
| **Required** | Optional |
| **Dublin Core** | `dc:source` |

Information about the origin and provenance of the item.

| Field | Type | Description |
|-------|------|-------------|
| `contributor` | String | Who contributed the item to the archive |
| `collection` | String | Named collection (e.g., "Oral Histories 2024") |
| `collection_identifier` | String | Stable local identifier or URI for the collection |
| `original_format` | String | Physical format before digitization |

---

### `format`

| Property | Value |
|----------|-------|
| **Type** | String (MIME type) |
| **Required** | Optional |
| **Dublin Core** | `dc:format` |
| **Pattern** | `^[a-z]+/[a-z0-9.+-]+$` |

Common values: `image/jpeg`, `image/png`, `audio/mpeg`, `video/mp4`, `application/pdf`, `text/plain`, `text/html`

---

### `technical`

| Property | Value |
|----------|-------|
| **Type** | Technical object |
| **Required** | Optional |
| **Purpose** | File-level technical and fixity metadata |

Use this section when the digital file itself needs technical description beyond a MIME
type.

| Field | Type | Description |
|-------|------|-------------|
| `file_uri` | String (URI) | Canonical URI for the digital file |
| `filename` | String | File name of the digital representation |
| `checksum` | String | Fixity checksum value |
| `checksum_algorithm` | Enum | `md5`, `sha1`, `sha256`, or `sha512` |
| `file_size_bytes` | Integer | File size in bytes |
| `duration_seconds` | Number | Duration for audio/video files |
| `page_count` | Integer | Number of pages in a document |
| `width_px` | Integer | Pixel width |
| `height_px` | Integer | Pixel height |

---

### `relation`

| Property | Value |
|----------|-------|
| **Type** | Array of UUIDs |
| **Required** | Optional |
| **Dublin Core** | `dc:relation` |

IDs of related DMS records. Use to link items that belong together (e.g., a story and its audio recording).

---

### `relation_detail`

| Property | Value |
|----------|-------|
| **Type** | Array of RelationDetail objects |
| **Required** | Optional |
| **Purpose** | Typed relationships to related records or resources |

Use this when the relationship itself matters, not just the existence of a link.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | String | Yes | Identifier or URI of the related record or resource |
| `relation_type` | Enum | Yes | Relationship type such as `transcription_of` or `derived_from` |
| `label` | String | No | Human-readable label for the related resource |
| `note` | String | No | Additional clarification |

**Allowed `relation_type` values:** `has_part`, `is_part_of`, `transcription_of`, `translation_of`, `recording_of`, `digitization_of`, `derived_from`, `references`, `accompanies`, `version_of`

---

### `coverage`

| Property | Value |
|----------|-------|
| **Type** | Coverage object |
| **Required** | Optional |
| **Dublin Core** | `dc:coverage` |

Temporal scope of the content.

| Field | Type | Description |
|-------|------|-------------|
| `start_date` | String (date) | Start of the period |
| `end_date` | String (date) | End of the period |
| `period` | String | Human-readable period name |

---

### `schema_version`

| Property | Value |
|----------|-------|
| **Type** | String (const `"1.1.0"`) |
| **Required** | Optional |
| **Dublin Core** | — |

The version of the DMS schema this record conforms to. Should always be `"1.1.0"` for the current schema.
