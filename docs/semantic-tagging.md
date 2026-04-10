# Semantic Tagging for DMS

> A practical guide for building community-managed DMS vocabularies and semantic tagging.

---

## Why This Matters

Strong discovery usually depends on two things working together:

- a controlled taxonomy with stable preferred terms
- a tagging service that applies those terms consistently across content

DMS does not need a massive central registry to benefit from the same approach. A smaller, community-led
taxonomy can still improve search, browsing, reporting, and long-term consistency.

The most useful implementation patterns are:

- terms live in named authorities such as Subject, Geography, Organization, Person, and Company
- terms have stable unique identifiers, preferred labels, and sometimes synonyms or related properties
- some vocabularies are hierarchical, while others are flat authority lists
- tagging output includes relevance scores and authority-specific enrichment
- taxonomy governance includes deprecated terms and change logs

---

## What DMS Already Does Well

DMS already has a solid foundation for semantic description:

- `subject` captures topical terms and keywords
- `location` captures place names, camp areas, and coordinates
- `creator` captures people and roles
- `relation` links records to each other
- JSON-LD support enables future linked-data publishing

The main opportunity is to make `subject` less ad hoc and more governed.

---

## DMS Vocabulary Principles

### 1. Prefer Controlled Terms Over One-Off Keywords

When possible, select terms from a shared list rather than inventing a new label for
every record.

Examples:

- Prefer `oral history` instead of alternating between `oral histories`, `interview story`, and `life story`
- Prefer one place label such as `Congo` or `DR Congo`, then use it consistently
- Prefer one people-group label such as `elders` instead of switching between `elder`, `older people`, and `senior community members`

### 2. Use Faceted Subjects

Try to cover a few different metadata dimensions instead of adding many similar tags.

Suggested facets:

- Item type: `oral history`, `photograph`, `field recording`
- Theme: `displacement`, `education`, `resilience`, `livelihood`
- Place: `market`, `community center`, `school area`
- Community or origin: `Congo`, `Burundi`, `Rwanda`, `Somalia`
- People: `women`, `youth`, `elders`, `artists`
- Time: `2015`, `2024`, `early settlement era`

### 3. Keep Preferred Labels Canonical

Choose one preferred label for each recurring concept and reuse it exactly.

Good practice:

- Keep a lightweight registry of approved subject terms
- Record synonyms in documentation or a future taxonomy file
- Use the preferred label in the record itself

A strong vocabulary service does this with unique identifiers plus preferred labels. DMS can start smaller by
maintaining canonical labels now, then add stable local IDs later without changing the
basic meaning of the records.

### 4. Put Nuance in `description`, Not in Long Tags

Tags should stay short and reusable. Rich narrative detail belongs in `description`.

Use:

- `displacement`
- `school area`
- `women`

Avoid turning a tag into a sentence or highly specific note that only fits one item.

### 5. Treat Relationships as Metadata, Not Just Text

A good DMS vocabulary layer should emphasize linked concepts by:

- linking related items through `relation`
- using `location` consistently for named places
- using `creator` for people and roles instead of burying names only in prose

DMS already approximates separate authorities for people, places, organizations, and
subjects through different fields even though
the current schema keeps `subject` itself as plain strings.

### 6. Plan for Governance, Not Just Entry

One of the strongest lessons from real-world vocabulary work is that taxonomy quality comes
from maintenance workflows, not just field definitions.

Useful governance patterns for DMS:

- keep a list of approved preferred terms
- record deprecated terms and their replacements
- track when the shared vocabulary changes
- document why a new canonical term was introduced
- review near-duplicates during batch ingest or editorial review

Even a simple markdown or CSV registry can provide this benefit at small scale.

### 7. Separate Manual Description from Machine Assistance

DMS should distinguish between the taxonomy itself and any future automated tagging
service that applies it:

- the vocabulary defines approved concepts
- contributors choose terms manually today
- future tooling can suggest terms automatically

This keeps the schema stable while leaving room for auto-tagging later.

---

## Recommended Workflow for DMS Contributors

1. Start with the title and description.
2. Identify the main format, theme, place, community/origin, and people facets.
3. Choose 3 to 10 preferred subject terms from the shared vocabulary.
4. Only create a new subject term when no existing label fits.
5. Reuse the new label consistently in future records.

If contributor tooling is added later, it should suggest existing preferred terms first,
then flag possible duplicates before allowing a brand-new label.

---

## Example

Instead of an uneven tag list like:

```json
"subject": ["interview story", "market life", "Congolese family journey", "hopeful"]
```

Prefer a reusable, faceted set like:

```json
"subject": [
  "oral history",
  "displacement",
  "market",
  "Congo",
  "family",
  "resilience"
]
```

---

## A Good DMS Taxonomy Starter Set

If the project wants to formalize tagging gradually, start with a small shared vocabulary
for the most common concepts:

- Formats: `oral history`, `photograph`, `field recording`, `document`, `poem`, `mural`
- Themes: `displacement`, `education`, `livelihood`, `community`, `health`, `memory`, `resilience`
- Places: `community center`, `market area`, `school area`, `health center`, `main ground`
- Communities/origins: `Congo`, `Burundi`, `Rwanda`, `Somalia`
- People: `women`, `youth`, `elders`, `artists`, `students`

This is small enough to manage manually while still creating much better consistency.

---

## What DMS Should Build First

These ideas translate well to DMS immediately:

- Authority thinking: treat themes, places, people, organizations, and collections as separate concept groups
- Preferred labels: use one canonical label for each recurring concept
- Enrichment: keep structured place and creator data outside freeform tags whenever possible
- Mappings: plan for mappings to outside vocabularies rather than replacing local language
- Governance: maintain deprecations and a simple change history for vocabulary updates

These are high-value even before building more advanced tooling.

---

## A Practical DMS Authority Model

DMS can support lightweight authorities with community-managed rules:

| Authority area | DMS equivalent today | Possible future improvement |
|---|---|---|
| Subject | `subject` tags | Local subject taxonomy with stable IDs |
| Geography | `location.name`, `location.area`, coordinates | Place authority file for camp and origin locations |
| Person | `creator.name`, `creator.role` | Person registry for recurring narrators, interviewers, artists |
| Organization | `creator.affiliation`, `source.contributor`, `source.collection` | Organization and collection authority lists |
| Company | Not central for most DMS records | Optional only if business archives become important |

This structure fits DMS well because the schema already separates several entity types.

---

## Relevance and Confidence

DMS tagging results could eventually include relevance scores for matched concepts, but DMS does not currently
store confidence or relevance, which is reasonable for human-authored records.

If DMS later adds automated tagging, consider keeping confidence outside the core record
or as optional workflow metadata so contributor-reviewed records remain authoritative.

---

## Deprecations and Change Tracking

A DMS vocabulary service should expose deprecated terms and vocabulary change logs through
dedicated APIs. The first version can still stay simple:

- maintain a `preferred_term -> deprecated aliases` list
- note vocabulary changes in a changelog or taxonomy registry
- document replacement terms when labels change

This helps keep historical records understandable without forcing immediate rewrites.

---

## Mappings and Interoperability

DMS can map its local subject taxonomy to outside vocabularies when useful:

- preserve local Dzaleka-first terminology in the record
- map those terms to external vocabularies in exports or documentation
- keep the local preferred label as the source of truth

This is especially compatible with DMS JSON-LD work, where external mappings can be added
without flattening community-specific meaning.

---

## Ontology Patterns Worth Reusing

A strong ontology layer adds another level beyond delivery: it shows how the taxonomy is
modeled, not just how it is published.

Useful patterns include:

- concept schemes and authorities for grouping terms
- `skos:broader` and `skos:related` for hierarchy and associations
- `skos:altLabel` for synonyms and alternate spellings
- `skos:exactMatch`, `skos:closeMatch`, and related mapping properties for external alignments
- `skos:changeNote` for documenting vocabulary changes
- `dc:created` and `dc:modified` for term lifecycle tracking
- `geo:lat` and `geo:long` for geographic authorities
- organization and person relationships such as membership, affiliation, and associated place

For DMS, the goal is not to clone anyone else's ontology wholesale. It is to reuse the
same modeling habits for any future DMS taxonomy files.

---

## How This Fits the Current DMS JSON-LD Context

DMS already has part of the needed foundation in [dms/data/schema/dms.jsonld](../dms/data/schema/dms.jsonld):

- Dublin Core and DCMI Terms for core descriptive fields
- FOAF for names and people-related metadata
- W3C Geo for latitude and longitude
- SKOS namespace availability for future controlled vocabularies

That means a future DMS taxonomy layer could be added without redesigning the record model.
The record can stay simple while separate concept files or authority files carry richer
semantic structure.

---

## A Sensible Future DMS Taxonomy Model

If DMS later publishes managed vocabularies, a good lightweight pattern would be:

- one concept scheme for subjects
- one place authority for camp areas and origin locations
- optional registries for organizations, collections, and recurring people
- stable local identifiers for each concept
- preferred labels plus alternate labels
- broader and related links where helpful
- change notes for renamed or deprecated terms
- optional external matches to SKOS-compatible vocabularies

This follows strong SKOS-based vocabulary patterns while staying proportionate to DMS.

---

## Recommended Ontology Features by DMS Priority

High-value first:

- `skos:prefLabel` for canonical labels
- `skos:altLabel` for synonyms and spelling variants
- `skos:broader` for simple hierarchies
- `skos:related` for cross-links
- `skos:changeNote` for deprecations and replacements

Useful once the taxonomy matures:

- `skos:exactMatch` and `skos:closeMatch` for external mappings
- `dc:created` and `dc:modified` for vocabulary maintenance
- place-level `geo:lat` and `geo:long`
- person or organization authority links for recurring contributors and collections

This staged approach keeps the system manageable while still moving toward richer semantics.

---

## Future Schema Direction

Without breaking the current schema, DMS could later add:

- a published local taxonomy or concept list for preferred labels
- stable identifiers for recurring entities such as places, organizations, or collections
- optional structured subject entries in a future major schema version
- vocabulary deprecation and change-log files
- optional machine-generated tagging suggestions with confidence metadata
- richer relationship mapping in JSON-LD exports

For now, the best next step is simple: keep the current `subject` array, but use it as
a controlled vocabulary field rather than a freeform keyword dump.
