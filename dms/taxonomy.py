"""
DMS taxonomy and vocabulary management.

Provides access to DMS controlled vocabularies, term subsets, deprecated terms,
change logs, structure summaries, and semantic-web serializations.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any


TAXONOMY_DIR = Path(__file__).resolve().parent / "data" / "taxonomy"

DEFAULT_CONTEXT = {
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dms": "https://github.com/Dzaleka-Connect/Dzaleka-Metadata-Standard/dms/data/schema#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "dcterms": "http://purl.org/dc/terms/",
    "schema": "https://schema.org/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "id": "@id",
    "type": "@type",
    "label": "skos:prefLabel",
    "definition": "skos:definition",
    "note": "skos:scopeNote",
    "history": "skos:historyNote",
    "changeNote": "skos:changeNote",
    "deprecated": "owl:deprecated",
    "mapping": "skos:exactMatch",
    "altLabel": "skos:altLabel",
    "broader": {"@id": "skos:broader", "@type": "@id"},
    "related": {"@id": "skos:related", "@type": "@id"},
    "supersededBy": {"@id": "dcterms:isReplacedBy", "@type": "@id"},
}

FALLBACK_VOCABULARIES = (
    "types",
    "roles",
    "access_levels",
    "relation_types",
    "consent_statuses",
    "sensitivity_markers",
)


def _humanize_term(term: str) -> str:
    return term.replace("_", " ").replace("-", " ").title()


def _fallback_vocabulary_specs() -> dict[str, dict[str, Any]]:
    from dms.schema import (
        get_access_levels,
        get_consent_statuses,
        get_creator_roles,
        get_relation_types,
        get_sensitivity_values,
        get_type_enum,
    )

    return {
        "types": {
            "scheme_id": "dms:HeritageTypes",
            "scheme_label": "DMS Heritage Item Types",
            "scheme_definition": "Primary categories for heritage items described with DMS.",
            "term_prefix": "dms:type",
            "terms": get_type_enum(),
        },
        "roles": {
            "scheme_id": "dms:Roles",
            "scheme_label": "DMS Creator Roles",
            "scheme_definition": "Roles used to describe how people contributed to a heritage item.",
            "term_prefix": "dms:role",
            "terms": get_creator_roles(),
        },
        "access_levels": {
            "scheme_id": "dms:AccessLevels",
            "scheme_label": "DMS Access Levels",
            "scheme_definition": "Access categories used to govern visibility and reuse of records.",
            "term_prefix": "dms:access",
            "terms": get_access_levels(),
        },
        "relation_types": {
            "scheme_id": "dms:RelationTypes",
            "scheme_label": "DMS Relation Types",
            "scheme_definition": "Relationship types used to connect records and derivatives.",
            "term_prefix": "dms:relation-type",
            "terms": get_relation_types(),
        },
        "consent_statuses": {
            "scheme_id": "dms:ConsentStatuses",
            "scheme_label": "DMS Consent Statuses",
            "scheme_definition": "Consent review states used for rights and access decisions.",
            "term_prefix": "dms:consent",
            "terms": get_consent_statuses(),
        },
        "sensitivity_markers": {
            "scheme_id": "dms:SensitivityMarkers",
            "scheme_label": "DMS Sensitivity Markers",
            "scheme_definition": "Sensitivity markers used to flag cultural, personal, or safety concerns.",
            "term_prefix": "dms:sensitivity",
            "terms": get_sensitivity_values(),
        },
    }


def _fallback_term_definition(vocabulary: str, term: str) -> str:
    if vocabulary == "types":
        return f"DMS heritage item type for {term.replace('_', ' ')}."
    if vocabulary == "roles":
        return f"DMS creator role for {term.replace('_', ' ')}."
    if vocabulary == "access_levels":
        return f"DMS access level describing {term.replace('-', ' ')} availability."
    if vocabulary == "relation_types":
        return f"DMS relation type describing when one item is {term.replace('_', ' ')} another."
    if vocabulary == "consent_statuses":
        return f"DMS consent review state for items marked as {term.replace('-', ' ')}."
    if vocabulary == "sensitivity_markers":
        return f"DMS sensitivity marker for {term.replace('-', ' ')} content."
    return f"DMS controlled term for {term.replace('_', ' ').replace('-', ' ')}."


def _term_short_id(term_id: str) -> str:
    if "/" in term_id:
        return term_id.rsplit("/", 1)[-1]
    if ":" in term_id:
        return term_id.rsplit(":", 1)[-1]
    return term_id


def infer_vocabulary_from_identifier(identifier: str) -> str | None:
    """Infer a managed DMS vocabulary name from a compact DMS term identifier."""
    raw = str(identifier or "")
    if "type/" in raw:
        return "types"
    if "role/" in raw:
        return "roles"
    if "access/" in raw:
        return "access_levels"
    if "relation-type/" in raw:
        return "relation_types"
    if "consent/" in raw:
        return "consent_statuses"
    if "sensitivity/" in raw:
        return "sensitivity_markers"
    return None


def is_managed_dms_identifier(identifier: str) -> bool:
    """Return True when an identifier belongs to a managed DMS vocabulary."""
    raw = str(identifier or "")
    return raw.startswith("dms:") and infer_vocabulary_from_identifier(raw) is not None


def _normalize_change_log(entries: list[Any]) -> list[dict]:
    normalized = []
    for entry in entries:
        if isinstance(entry, dict):
            item = dict(entry)
            item.setdefault("message", "")
            normalized.append(item)
            continue
        if isinstance(entry, str):
            date_part = ""
            message = entry
            if ": " in entry:
                date_part, message = entry.split(": ", 1)
            normalized.append(
                {
                    "date": date_part or None,
                    "message": message,
                }
            )
    return normalized


def _build_structure_summary(vocabulary: str, taxonomy: dict) -> dict:
    concepts = taxonomy.get("hasTopConcept", [])
    deprecated_terms = taxonomy.get("deprecated", [])
    all_terms = concepts + deprecated_terms
    hierarchy_links = any(term.get("broader") for term in all_terms)
    related_links = any(term.get("related") for term in all_terms)

    return {
        "vocabulary": vocabulary,
        "scheme_id": taxonomy.get("id"),
        "label": taxonomy.get("label"),
        "kind": "hierarchical" if hierarchy_links else "flat",
        "top_concept_count": len(concepts),
        "term_count": len(concepts),
        "deprecated_term_count": len(deprecated_terms),
        "has_hierarchy": hierarchy_links,
        "has_related_links": related_links,
        "supports_deprecations": bool(deprecated_terms),
        "supports_change_log": bool(taxonomy.get("changeLog")),
        "available_formats": ["json", "jsonld", "ttl", "rdfxml", "html"],
    }


def _normalize_taxonomy(vocabulary: str, taxonomy: dict) -> dict:
    data = copy.deepcopy(taxonomy)
    context = dict(DEFAULT_CONTEXT)
    context.update(data.get("@context", {}))
    data["@context"] = context

    data.setdefault("vocabulary", vocabulary)
    data.setdefault("type", "skos:ConceptScheme")
    data.setdefault("hasTopConcept", [])
    data.setdefault("deprecated", [])
    data["changeLog"] = _normalize_change_log(
        data.get("changeLog", data.get("history", []))
    )

    for concept in data["hasTopConcept"]:
        concept.setdefault("type", "skos:Concept")
        concept.setdefault("inScheme", data["id"])

    for concept in data["deprecated"]:
        concept.setdefault("type", "skos:Concept")
        concept.setdefault("inScheme", data["id"])
        concept["deprecated"] = True

    data["structure"] = _build_structure_summary(vocabulary, data)
    return data


@lru_cache(maxsize=16)
def load_taxonomy(vocabulary: str) -> dict:
    """Load a taxonomy file from the data/taxonomy directory."""
    file_path = TAXONOMY_DIR / f"{vocabulary}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as handle:
            return _normalize_taxonomy(vocabulary, json.load(handle))
    return generate_fallback_taxonomy(vocabulary)


def generate_fallback_taxonomy(vocabulary: str) -> dict:
    """Generate a flat DMS vocabulary from schema enums when no file exists."""
    specs = _fallback_vocabulary_specs()
    if vocabulary not in specs:
        raise FileNotFoundError(f"Vocabulary '{vocabulary}' not found.")

    spec = specs[vocabulary]
    scheme = {
        "@context": dict(DEFAULT_CONTEXT),
        "id": spec["scheme_id"],
        "type": "skos:ConceptScheme",
        "label": spec["scheme_label"],
        "definition": spec["scheme_definition"],
        "hasTopConcept": [],
        "deprecated": [],
        "changeLog": [
            {
                "message": "Vocabulary terms are generated directly from the current DMS schema.",
                "source": "dms-schema",
            }
        ],
    }

    for term in spec["terms"]:
        scheme["hasTopConcept"].append(
            {
                "id": f"{spec['term_prefix']}/{term}",
                "type": "skos:Concept",
                "label": _humanize_term(term),
                "definition": _fallback_term_definition(vocabulary, term),
            }
        )

    return _normalize_taxonomy(vocabulary, scheme)


def get_vocabulary_list() -> list[str]:
    """Return a list of available vocabularies."""
    json_vocabularies = sorted(path.stem for path in TAXONOMY_DIR.glob("*.json"))
    return sorted(set(json_vocabularies).union(FALLBACK_VOCABULARIES))


def _all_terms(taxonomy: dict, include_deprecated: bool = False) -> list[dict]:
    terms = list(taxonomy.get("hasTopConcept", []))
    if include_deprecated:
        terms.extend(taxonomy.get("deprecated", []))
    return terms


def _matches_term_identifier(term: dict, term_id: str) -> bool:
    candidate = term.get("id", "")
    short_id = _term_short_id(candidate)
    return term_id == candidate or term_id == short_id


def _lookup_term(taxonomy: dict, term_id: str) -> dict | None:
    for term in _all_terms(taxonomy, include_deprecated=True):
        if _matches_term_identifier(term, term_id):
            result = dict(term)
            result["short_id"] = _term_short_id(result.get("id", term_id))
            return result
    return None


def get_terms(
    vocabulary: str,
    ids: list[str] | None = None,
    q: str | None = None,
    include_deprecated: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Retrieve term sets from a vocabulary with optional filtering."""
    taxonomy = load_taxonomy(vocabulary)
    terms = _all_terms(taxonomy, include_deprecated=include_deprecated)

    if ids:
        wanted = {item.strip() for item in ids if item.strip()}
        terms = [
            term
            for term in terms
            if term.get("id") in wanted or _term_short_id(term.get("id", "")) in wanted
        ]

    if q:
        needle = q.strip().lower()
        terms = [
            term
            for term in terms
            if needle in term.get("label", "").lower()
            or needle in term.get("definition", "").lower()
            or needle in term.get("id", "").lower()
        ]

    if offset:
        terms = terms[offset:]
    if limit is not None:
        terms = terms[:limit]
    return terms


def get_subset_taxonomy(
    vocabulary: str,
    ids: list[str] | None = None,
    q: str | None = None,
    include_deprecated: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    """Return a copy of a vocabulary containing only the requested terms."""
    taxonomy = copy.deepcopy(load_taxonomy(vocabulary))
    all_terms = get_terms(
        vocabulary,
        ids=ids,
        q=q,
        include_deprecated=include_deprecated,
        limit=limit,
        offset=offset,
    )
    active_ids = {term.get("id") for term in all_terms if not term.get("deprecated")}
    deprecated_ids = {term.get("id") for term in all_terms if term.get("deprecated")}
    taxonomy["hasTopConcept"] = [
        term for term in taxonomy.get("hasTopConcept", []) if term.get("id") in active_ids
    ]
    taxonomy["deprecated"] = [
        term for term in taxonomy.get("deprecated", []) if term.get("id") in deprecated_ids
    ]
    taxonomy["structure"] = _build_structure_summary(vocabulary, taxonomy)
    return taxonomy


def get_term_info(vocabulary: str, term_id: str) -> dict | None:
    """Retrieve information about a specific term within a vocabulary."""
    taxonomy = load_taxonomy(vocabulary)
    term = _lookup_term(taxonomy, term_id)
    if term is None:
        return None
    term["changeLog"] = get_change_log(vocabulary, term_id=term["short_id"])
    return term


def get_deprecated_terms(vocabulary: str) -> list[dict]:
    """Retrieve deprecated terms for a vocabulary."""
    taxonomy = load_taxonomy(vocabulary)
    return list(taxonomy.get("deprecated", []))


def get_change_log(vocabulary: str, term_id: str | None = None) -> list[dict]:
    """Retrieve the change log for a vocabulary or a specific term."""
    taxonomy = load_taxonomy(vocabulary)
    entries = list(taxonomy.get("changeLog", []))

    if term_id is None:
        return entries

    term = _lookup_term(taxonomy, term_id)
    if term is None:
        return []

    specific_entries = [
        entry
        for entry in entries
        if entry.get("term_id") in {term.get("id"), term.get("short_id")}
    ]

    if term.get("changeLog"):
        specific_entries.extend(term.get("changeLog", []))

    change_notes = term.get("changeNote", [])
    if isinstance(change_notes, str):
        change_notes = [change_notes]
    for note in change_notes:
        specific_entries.append({"message": note})

    if term.get("deprecated"):
        replacement = term.get("supersededBy")
        message = "Term is deprecated."
        if replacement:
            message = f"Term is deprecated and replaced by {replacement}."
        specific_entries.append({"message": message})

    seen = set()
    deduplicated = []
    for entry in specific_entries:
        fingerprint = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        deduplicated.append(entry)
    return deduplicated


def get_vocabulary_structure(vocabulary: str) -> dict:
    """Return structural information about a vocabulary."""
    taxonomy = load_taxonomy(vocabulary)
    return dict(taxonomy.get("structure", {}))


def _context_prefixes(taxonomy: dict) -> dict[str, str]:
    prefixes = {}
    context = taxonomy.get("@context", {})
    for key, value in context.items():
        if isinstance(value, str) and value.startswith(("http://", "https://", "urn:")):
            prefixes[key] = value
    return prefixes


def _expand_identifier(value: Any, taxonomy: dict) -> str:
    if not isinstance(value, str):
        return ""
    if value.startswith(("http://", "https://", "urn:")):
        return value
    if ":" in value:
        prefix, local = value.split(":", 1)
        base = _context_prefixes(taxonomy).get(prefix)
        if base:
            return f"{base}{local}"
    return value


def _term_triples(taxonomy: dict, term: dict) -> list[tuple[str, str, Any, bool]]:
    triples: list[tuple[str, str, Any, bool]] = []
    term_uri = _expand_identifier(term.get("id"), taxonomy)
    scheme_uri = _expand_identifier(taxonomy.get("id"), taxonomy)
    triples.append((term_uri, "rdf:type", _expand_identifier("skos:Concept", taxonomy), True))
    triples.append((term_uri, "skos:inScheme", scheme_uri, True))

    if term.get("label"):
        triples.append((term_uri, "skos:prefLabel", term["label"], False))
    if term.get("definition"):
        triples.append((term_uri, "skos:definition", term["definition"], False))
    if term.get("mapping"):
        triples.append((term_uri, "skos:exactMatch", _expand_identifier(term["mapping"], taxonomy), True))
    if term.get("supersededBy"):
        triples.append((term_uri, "dcterms:isReplacedBy", _expand_identifier(term["supersededBy"], taxonomy), True))
    if term.get("deprecated"):
        triples.append((term_uri, "owl:deprecated", "true", False))

    alt_labels = term.get("altLabel", [])
    if isinstance(alt_labels, str):
        alt_labels = [alt_labels]
    for alt_label in alt_labels:
        triples.append((term_uri, "skos:altLabel", alt_label, False))

    related_values = term.get("related", [])
    if isinstance(related_values, str):
        related_values = [related_values]
    for related in related_values:
        triples.append((term_uri, "skos:related", _expand_identifier(related, taxonomy), True))

    broader_values = term.get("broader", [])
    if isinstance(broader_values, str):
        broader_values = [broader_values]
    for broader in broader_values:
        triples.append((term_uri, "skos:broader", _expand_identifier(broader, taxonomy), True))

    change_entries = term.get("changeLog", [])
    if isinstance(change_entries, str):
        change_entries = [{"message": change_entries}]
    for entry in change_entries:
        message = entry if isinstance(entry, str) else entry.get("message")
        if message:
            triples.append((term_uri, "skos:changeNote", message, False))

    change_notes = term.get("changeNote", [])
    if isinstance(change_notes, str):
        change_notes = [change_notes]
    for note in change_notes:
        triples.append((term_uri, "skos:changeNote", note, False))

    return triples


def _scheme_triples(taxonomy: dict) -> list[tuple[str, str, Any, bool]]:
    triples: list[tuple[str, str, Any, bool]] = []
    scheme_uri = _expand_identifier(taxonomy.get("id"), taxonomy)
    triples.append((scheme_uri, "rdf:type", _expand_identifier("skos:ConceptScheme", taxonomy), True))

    if taxonomy.get("label"):
        triples.append((scheme_uri, "skos:prefLabel", taxonomy["label"], False))
    if taxonomy.get("definition"):
        triples.append((scheme_uri, "skos:definition", taxonomy["definition"], False))

    for term in taxonomy.get("hasTopConcept", []):
        triples.append((scheme_uri, "skos:hasTopConcept", _expand_identifier(term.get("id"), taxonomy), True))

    for entry in taxonomy.get("changeLog", []):
        if entry.get("message"):
            triples.append((scheme_uri, "skos:historyNote", entry["message"], False))

    return triples


def _escape_turtle_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def taxonomy_to_jsonld(taxonomy: dict) -> dict:
    """Return a JSON-LD representation of a taxonomy document."""
    return copy.deepcopy(taxonomy)


def taxonomy_to_turtle(taxonomy: dict) -> str:
    """Serialize a taxonomy document as Turtle."""
    prefixes = _context_prefixes(taxonomy)
    prefixes["rdf"] = DEFAULT_CONTEXT["rdf"]
    prefixes["dcterms"] = DEFAULT_CONTEXT["dcterms"]
    lines = [f"@prefix {name}: <{uri}> ." for name, uri in sorted(prefixes.items())]
    lines.append("")

    triples = _scheme_triples(taxonomy)
    for term in taxonomy.get("hasTopConcept", []):
        triples.extend(_term_triples(taxonomy, term))
    for term in taxonomy.get("deprecated", []):
        triples.extend(_term_triples(taxonomy, term))

    for subject, predicate, obj, is_uri in triples:
        if is_uri:
            object_repr = f"<{obj}>"
        elif obj in {"true", "false"}:
            object_repr = obj
        else:
            object_repr = f"\"{_escape_turtle_literal(str(obj))}\""
        lines.append(f"<{subject}> {predicate} {object_repr} .")

    return "\n".join(lines) + "\n"


def taxonomy_to_rdfxml(taxonomy: dict) -> str:
    """Serialize a taxonomy document as RDF/XML."""
    prefixes = _context_prefixes(taxonomy)
    prefixes["rdf"] = DEFAULT_CONTEXT["rdf"]
    prefixes["dcterms"] = DEFAULT_CONTEXT["dcterms"]

    namespace_attrs = " ".join(
        f'xmlns:{prefix}="{escape(uri)}"' for prefix, uri in sorted(prefixes.items())
    )
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', f"<rdf:RDF {namespace_attrs}>"]

    scheme_uri = escape(_expand_identifier(taxonomy.get("id"), taxonomy))
    lines.append(f'  <skos:ConceptScheme rdf:about="{scheme_uri}">')
    if taxonomy.get("label"):
        lines.append(f"    <skos:prefLabel>{escape(str(taxonomy['label']))}</skos:prefLabel>")
    if taxonomy.get("definition"):
        lines.append(f"    <skos:definition>{escape(str(taxonomy['definition']))}</skos:definition>")
    for term in taxonomy.get("hasTopConcept", []):
        term_uri = escape(_expand_identifier(term.get("id"), taxonomy))
        lines.append(f'    <skos:hasTopConcept rdf:resource="{term_uri}" />')
    for entry in taxonomy.get("changeLog", []):
        if entry.get("message"):
            lines.append(f"    <skos:historyNote>{escape(entry['message'])}</skos:historyNote>")
    lines.append("  </skos:ConceptScheme>")

    for term in taxonomy.get("hasTopConcept", []) + taxonomy.get("deprecated", []):
        term_uri = escape(_expand_identifier(term.get("id"), taxonomy))
        lines.append(f'  <skos:Concept rdf:about="{term_uri}">')
        lines.append(f'    <skos:inScheme rdf:resource="{scheme_uri}" />')
        if term.get("label"):
            lines.append(f"    <skos:prefLabel>{escape(str(term['label']))}</skos:prefLabel>")
        if term.get("definition"):
            lines.append(f"    <skos:definition>{escape(str(term['definition']))}</skos:definition>")
        if term.get("mapping"):
            mapping_uri = escape(_expand_identifier(term["mapping"], taxonomy))
            lines.append(f'    <skos:exactMatch rdf:resource="{mapping_uri}" />')
        if term.get("supersededBy"):
            replacement_uri = escape(_expand_identifier(term["supersededBy"], taxonomy))
            lines.append(f'    <dcterms:isReplacedBy rdf:resource="{replacement_uri}" />')
        if term.get("deprecated"):
            lines.append('    <owl:deprecated rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">true</owl:deprecated>')
        alt_labels = term.get("altLabel", [])
        if isinstance(alt_labels, str):
            alt_labels = [alt_labels]
        for alt_label in alt_labels:
            lines.append(f"    <skos:altLabel>{escape(str(alt_label))}</skos:altLabel>")
        lines.append("  </skos:Concept>")

    lines.append("</rdf:RDF>")
    return "\n".join(lines) + "\n"


def term_to_html(vocabulary: str, term_info: dict) -> str:
    """Render term information as HTML."""
    label = term_info.get("label", "Untitled Term")
    definition = term_info.get("definition", "No definition provided.")
    mapping = term_info.get("mapping")
    change_log = term_info.get("changeLog", [])
    alt_labels = term_info.get("altLabel", [])
    if isinstance(alt_labels, str):
        alt_labels = [alt_labels]

    change_items = "".join(
        f"<li>{escape(entry.get('message', ''))}</li>"
        for entry in change_log
        if entry.get("message")
    ) or "<li>No recorded changes.</li>"
    alt_label_html = "".join(f"<li>{escape(label_value)}</li>" for label_value in alt_labels)

    mapping_html = ""
    if mapping:
        mapping_html = (
            "<h3>External Mapping</h3>"
            f"<p><span class=\"mapping\">{escape(str(mapping))}</span></p>"
        )

    deprecated_html = ""
    if term_info.get("deprecated"):
        replacement = term_info.get("supersededBy")
        deprecated_html = (
            "<div class=\"deprecated\">"
            "<strong>Deprecated</strong>"
            f"{' Replaced by ' + escape(str(replacement)) + '.' if replacement else '.'}"
            "</div>"
        )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{escape(label)} - DMS Vocabulary</title>
        <style>
            body {{ font-family: sans-serif; line-height: 1.6; max-width: 840px; margin: 2rem auto; padding: 0 1rem; color: #1f2937; }}
            h1 {{ color: #0f172a; border-bottom: 2px solid #10b981; padding-bottom: 0.5rem; }}
            .meta {{ background: #f8fafc; padding: 1rem; border-radius: 10px; border: 1px solid #e2e8f0; }}
            .label-id {{ font-family: monospace; color: #64748b; }}
            .mapping {{ display: inline-block; background: #dcfce7; color: #166534; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.9rem; }}
            .deprecated {{ margin: 1rem 0; padding: 0.75rem 1rem; border-radius: 8px; background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }}
        </style>
    </head>
    <body>
        <p><a href="/api/taxonomy/{escape(vocabulary)}">← Back to {escape(vocabulary)}</a></p>
        <h1>{escape(label)}</h1>
        <p class="label-id">ID: {escape(str(term_info.get('id', '')))}</p>
        {deprecated_html}
        <div class="meta">
            <h3>Definition</h3>
            <p>{escape(str(definition))}</p>
            {mapping_html}
            <h3>Alternative Labels</h3>
            <ul>{alt_label_html or '<li>None recorded.</li>'}</ul>
            <h3>Change Log</h3>
            <ul>{change_items}</ul>
        </div>
    </body>
    </html>
    """
