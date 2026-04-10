# Best Practices for Metadata Entry

> Guidelines for creating high-quality DMS records that are discoverable, accurate, and respectful of community heritage.

---

## General Principles

### 1. Be Specific and Descriptive

Avoid vague or generic entries. Good metadata helps people **find** and **understand** heritage items.

| ❌ Avoid | ✅ Prefer |
|----------|----------|
| "Photo" | "Market Day at Dzaleka" |
| "A story" | "Journey to Dzaleka: A Story of Hope" |
| "Document" | "Community School Registration Records, 2018" |
| "Some music" | "Traditional Songs of the Great Lakes Region" |

### 2. Write for Discovery

Think about how someone might search for this item. Include the terms they would use in the title, description, and subject tags.

### 3. Respect Community Voices

- Use the names and terms that community members use
- Preserve original titles when possible
- Note the original language of the content
- Record roles accurately (narrator, interviewer, photographer, etc.)

### 4. Be Consistent

- Use the same format for similar items
- Apply tags consistently across records
- Follow the same naming conventions for locations and areas
- Reuse the same preferred subject terms instead of near-duplicates

---

## Writing Titles

- Make titles **concise but informative** (under 100 words is ideal)
- Include the **subject** and **context** when possible
- Add **dates** or **locations** to distinguish similar items
- Use the item's **original title** if one exists

**Examples:**
```
✅ "Journey to Dzaleka: A Story of Hope"
✅ "Market Day at Dzaleka, May 2024"
✅ "Community School Registration Records, 2018"

❌ "Photo 001"
❌ "Interview"
❌ "Untitled"
```

---

## Writing Descriptions

Descriptions should tell the story behind the item. A good description answers:

1. **What** is this item?
2. **Who** is involved?
3. **When** did it happen or was it created?
4. **Where** did it take place?
5. **Why** does it matter?

**Aim for 2–5 sentences.** Provide enough context for someone unfamiliar with Dzaleka to understand the significance.

**Example:**
> "An oral history account of a Congolese family's journey from Bukavu to Dzaleka Refugee Camp in 2015. The narrator describes the challenges of displacement, the experience of crossing borders, and the sense of community found upon arrival at Dzaleka. This story captures themes of resilience, loss, and rebuilding life in a new place."

---

## Choosing Tags (Subject)

Tags are keywords that help people discover your record. Follow these guidelines:

Think taxonomy-first: consistent, reusable terms make records easier to find and manage.
DMS can apply that principle at a community scale by keeping a shared list
of preferred labels for subjects, places, themes, and people groups.

### Do:
- Use **3–10 tags** per record
- Prefer terms from a shared vocabulary before inventing a new label
- Include both **broad** terms ("oral history") and **specific** terms ("Congo")
- Add **cultural** terms where appropriate
- Use **lowercase** for consistency

### Don't:
- Mix near-duplicates such as "dr congo", "drc", and "congo" for the same concept
- Repeat information already in the title
- Use overly broad tags alone ("important", "good")
- Use abbreviations without explanation

**Suggested tag categories:**

| Category | Examples |
|----------|----------|
| Item type | oral history, photograph, field recording |
| Theme | displacement, resilience, education, community |
| Culture/origin | Congo, Burundi, Rwanda, Somalia |
| Location | market, school, community center |
| People | women, youth, elders |
| Time | 2024, early settlement era |

When a new concept is genuinely needed, add it deliberately and then reuse that same
label across future records. This creates a small but reliable local taxonomy instead
of a drifting list of one-off keywords.

---

## Location Data

### Camp Areas

Use consistent names for Dzaleka camp areas:

- `Section A`, `Section B`, `Section C`
- `Market Area`
- `Community Center`
- `Main Ground`
- `School Area`
- `Health Center`

### Coordinates

Dzaleka Refugee Camp approximate coordinates:
- **Latitude:** -13.7833
- **Longitude:** 33.9833

When possible, provide specific coordinates for the exact location within the camp.

---

## Rights and Access

### Choosing a License

| License | When to use |
|---------|-------------|
| `CC-BY-4.0` | Open sharing with attribution required |
| `CC-BY-NC-4.0` | Sharing with attribution, no commercial use |
| `CC-BY-NC-ND-4.0` | Share only as-is, no modifications |
| `CC0-1.0` | Public domain dedication |

When in doubt, use **CC-BY-NC-4.0** — it protects the community's rights while allowing educational use.

### Access Levels

| Level | When to use |
|-------|-------------|
| `public` | Safe for anyone to view — no sensitive information |
| `restricted` | Contains personal data or sensitive content — requires permission |
| `community-only` | Sacred, private, or culturally sensitive — for Dzaleka community only |

### Important Considerations

- ⚠️ **Always get consent** from people featured in stories, photos, or recordings
- ⚠️ **Protect privacy** — do not include personal identifiers in public records
- ⚠️ **Respect cultural sensitivity** — some heritage items may not be appropriate for public sharing
- ⚠️ **Credit creators** — always list the original creator(s) and their roles

When possible, use the richer v1.1 rights fields to document review context:

- Set `consent_status` explicitly when consent has been obtained, is pending, or is unknown
- Add `sensitivity` markers for issues such as trauma, sacred knowledge, minors, or personal data
- Use `access_note` to explain why a record is restricted or how it should be reused safely

---

## Working with Oral Histories

Oral histories require special care:

1. **Record both participants** — list the narrator and the interviewer as creators
2. **Specify the original language** — set `language` to the language spoken in the interview
3. **Note the format** — specify whether it's a transcription (`text/plain`) or audio recording (`audio/mpeg`)
4. **Respect the narrator's wishes** — set access level as agreed with the narrator
5. **Preserve context** — describe the circumstances of the interview in the description
6. **Capture the relationship** — if a transcript, translation, or derivative exists, use `relation_detail` to record how the items are connected
7. **Record fixity when available** — for preservation copies, add checksums and file metadata in `technical`

---

## Batch Entry with CSV

When entering multiple records at once:

1. Download or copy the [batch.csv template](../examples/batch.csv)
2. Fill in one row per record
3. Use `|` (pipe) to separate multiple values in a single column
   - Creator names: `Marie Consolée|Jean-Baptiste Mushimiyimana`
   - Subject tags: `oral history|displacement|Congo`
   - Sensitivity tags: `trauma-sensitive|personal-data`
4. Run `dms convert csv2json your-batch.csv` to create JSON records
5. Validate with `dms validate --dir output/`

---

## Quality Checklist

Before submitting a record, verify:

- [ ] Title is specific and descriptive
- [ ] Type is correctly chosen
- [ ] Description provides meaningful context (2+ sentences)
- [ ] Language code is correct
- [ ] Creator(s) are listed with correct roles
- [ ] At least 3 subject tags are included
- [ ] Structured identifiers are added where local authority records exist
- [ ] Location is specified (at minimum, the place name)
- [ ] Rights and access level are set appropriately
- [ ] Consent has been obtained from all people featured
- [ ] Technical metadata is added for preservation files when available
- [ ] Typed relations are recorded for transcripts, translations, and derivatives
- [ ] The record validates: `dms validate your-record.json`
