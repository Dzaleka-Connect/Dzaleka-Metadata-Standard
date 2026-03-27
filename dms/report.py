"""
DMS Report Generator

Generate browsable HTML or Markdown reports from a directory
of DMS records — acts as a lightweight digital catalogue.
"""

import json
from pathlib import Path
from datetime import datetime

from rich.console import Console

console = Console()


def generate_html_report(
    dir_path: str | Path,
    output_path: str | Path | None = None,
    title: str = "Dzaleka Heritage Collection",
) -> str:
    """Generate an HTML catalogue from a directory of DMS records.

    Args:
        dir_path: Directory containing DMS JSON files.
        output_path: Output HTML file path.
        title: Title for the report.

    Returns:
        The HTML content as a string.
    """
    dir_path = Path(dir_path)
    records = _load_all_records(dir_path)

    # Group by type
    by_type: dict[str, list[dict]] = {}
    for rec in records:
        t = rec.get("type", "other")
        by_type.setdefault(t, []).append(rec)

    # Count stats
    total = len(records)
    type_counts = {t: len(recs) for t, recs in sorted(by_type.items())}
    languages = set(r.get("language", "unknown") for r in records)
    creators = set()
    for r in records:
        for c in r.get("creator", []):
            if isinstance(c, dict) and "name" in c:
                creators.add(c["name"])

    html = _build_html(title, records, by_type, type_counts, total, languages, creators)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        console.print(f"  [green]✓ Report generated: {output_path}[/green]")

    return html


def generate_md_report(
    dir_path: str | Path,
    output_path: str | Path | None = None,
    title: str = "Dzaleka Heritage Collection",
) -> str:
    """Generate a Markdown catalogue from a directory of DMS records."""
    dir_path = Path(dir_path)
    records = _load_all_records(dir_path)

    by_type: dict[str, list[dict]] = {}
    for rec in records:
        t = rec.get("type", "other")
        by_type.setdefault(t, []).append(rec)

    lines = [
        f"# {title}",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        f"**Total records:** {len(records)}  ",
        f"**Types:** {', '.join(sorted(by_type.keys()))}  ",
        "",
        "---",
        "",
    ]

    for type_name, recs in sorted(by_type.items()):
        lines.append(f"## {type_name.title()} ({len(recs)})")
        lines.append("")

        for rec in recs:
            lines.append(f"### {rec.get('title', 'Untitled')}")
            lines.append("")
            lines.append(f"- **ID:** `{rec.get('id', '—')}`")
            lines.append(f"- **Language:** {rec.get('language', '—')}")

            creators = rec.get("creator", [])
            if creators and isinstance(creators, list):
                names = ", ".join(
                    f"{c.get('name', '')} ({c.get('role', '')})"
                    for c in creators if isinstance(c, dict)
                )
                lines.append(f"- **Creator(s):** {names}")

            date_info = rec.get("date", {})
            if isinstance(date_info, dict) and date_info.get("created"):
                lines.append(f"- **Created:** {date_info['created']}")

            subjects = rec.get("subject", [])
            if subjects and isinstance(subjects, list):
                lines.append(f"- **Subjects:** {', '.join(subjects)}")

            location = rec.get("location", {})
            if isinstance(location, dict) and location.get("name"):
                loc_str = location["name"]
                if location.get("area"):
                    loc_str += f" — {location['area']}"
                lines.append(f"- **Location:** {loc_str}")

            rights = rec.get("rights", {})
            if isinstance(rights, dict):
                if rights.get("license"):
                    lines.append(f"- **License:** {rights['license']}")
                if rights.get("access_level"):
                    lines.append(f"- **Access:** {rights['access_level']}")

            desc = rec.get("description", "")
            if desc:
                lines.append(f"\n> {desc}")

            lines.append("")

    md = "\n".join(lines)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
        console.print(f"  [green]✓ Report generated: {output_path}[/green]")

    return md


def _load_all_records(dir_path: Path) -> list[dict]:
    """Load all valid DMS records from a directory."""
    records = []
    for jf in sorted(dir_path.glob("*.json")):
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data["_source_file"] = jf.name
                records.append(data)
            elif isinstance(data, list):
                for rec in data:
                    if isinstance(rec, dict):
                        rec["_source_file"] = jf.name
                        records.append(rec)
        except (json.JSONDecodeError, OSError):
            pass
    return records


def _build_html(
    title: str,
    records: list[dict],
    by_type: dict[str, list[dict]],
    type_counts: dict[str, int],
    total: int,
    languages: set[str],
    creators: set[str],
) -> str:
    """Build the HTML report string."""

    type_badges = "\n".join(
        f'<span class="badge badge-{t}">{t} <strong>{c}</strong></span>'
        for t, c in sorted(type_counts.items())
    )

    type_sections = ""
    for type_name, recs in sorted(by_type.items()):
        cards = ""
        for rec in recs:
            creator_list = rec.get("creator", [])
            creator_html = ", ".join(
                f'{c.get("name", "")} <em>({c.get("role", "")})</em>'
                for c in creator_list if isinstance(c, dict)
            ) if isinstance(creator_list, list) else ""

            subjects = rec.get("subject", [])
            tags_html = " ".join(
                f'<span class="tag">{s}</span>'
                for s in subjects
            ) if isinstance(subjects, list) else ""

            desc = rec.get("description", "")
            short_desc = desc[:200] + "…" if len(desc) > 200 else desc

            date_info = rec.get("date", {})
            date_str = date_info.get("created", "") if isinstance(date_info, dict) else ""

            rights = rec.get("rights", {})
            access = rights.get("access_level", "") if isinstance(rights, dict) else ""
            license_str = rights.get("license", "") if isinstance(rights, dict) else ""

            location = rec.get("location", {})
            loc_str = ""
            if isinstance(location, dict) and location.get("name"):
                loc_str = location["name"]
                if location.get("area"):
                    loc_str += f" — {location['area']}"

            cards += f"""
            <div class="card">
                <div class="card-header">
                    <h3>{rec.get("title", "Untitled")}</h3>
                    <span class="badge badge-{type_name}">{type_name}</span>
                </div>
                <p class="desc">{short_desc}</p>
                <div class="meta">
                    {"<div><strong>Creator:</strong> " + creator_html + "</div>" if creator_html else ""}
                    {"<div><strong>Date:</strong> " + date_str + "</div>" if date_str else ""}
                    {"<div><strong>Location:</strong> " + loc_str + "</div>" if loc_str else ""}
                    <div><strong>Language:</strong> {rec.get("language", "—")}</div>
                    {"<div><strong>Access:</strong> " + access + "</div>" if access else ""}
                    {"<div><strong>License:</strong> " + license_str + "</div>" if license_str else ""}
                </div>
                {"<div class='tags'>" + tags_html + "</div>" if tags_html else ""}
                <div class="id">ID: {rec.get("id", "—")}</div>
            </div>"""

        type_sections += f"""
        <section class="type-section" id="type-{type_name}">
            <h2>{type_name.title()} ({len(recs)})</h2>
            <div class="card-grid">{cards}
            </div>
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg: #0f1419;
            --surface: #1a2332;
            --surface2: #243447;
            --text: #e7e9ea;
            --text-dim: #8899a6;
            --accent: #1d9bf0;
            --accent2: #7856ff;
            --green: #00ba7c;
            --orange: #ff7a00;
            --red: #f4212e;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        header {{
            background: linear-gradient(135deg, var(--surface) 0%, #0d2137 100%);
            border-bottom: 1px solid var(--surface2);
            padding: 2.5rem 2rem;
            text-align: center;
        }}
        header h1 {{
            font-size: 2rem;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        header .subtitle {{ color: var(--text-dim); font-size: 0.95rem; }}
        .stats {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1.2rem;
            flex-wrap: wrap;
        }}
        .stat {{
            text-align: center;
        }}
        .stat .num {{
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--accent);
        }}
        .stat .label {{ font-size: 0.8rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; }}
        .badges {{
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            background: var(--surface2);
            color: var(--text-dim);
        }}
        .badge-story {{ background: #1a3a5c; color: #60a5fa; }}
        .badge-photo {{ background: #3a1a3a; color: #c084fc; }}
        .badge-document {{ background: #1a3a2a; color: #4ade80; }}
        .badge-audio {{ background: #3a2a1a; color: #fb923c; }}
        .badge-video {{ background: #3a1a2a; color: #f472b6; }}
        .badge-event {{ background: #2a2a1a; color: #fbbf24; }}
        .badge-map {{ background: #1a2a3a; color: #67e8f9; }}
        .badge-artwork {{ background: #2a1a3a; color: #a78bfa; }}
        .badge-site {{ background: #1a3a3a; color: #2dd4bf; }}
        .badge-poem {{ background: #3a1a1a; color: #fca5a5; }}
        main {{ max-width: 1100px; margin: 0 auto; padding: 2rem; }}
        .type-section {{ margin-bottom: 3rem; }}
        .type-section h2 {{
            font-size: 1.4rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--surface2);
            color: var(--text);
        }}
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 1rem;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--surface2);
            border-radius: 12px;
            padding: 1.25rem;
            transition: border-color 0.2s, transform 0.2s;
        }}
        .card:hover {{
            border-color: var(--accent);
            transform: translateY(-2px);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.5rem;
            margin-bottom: 0.75rem;
        }}
        .card-header h3 {{ font-size: 1.05rem; line-height: 1.3; }}
        .desc {{ color: var(--text-dim); font-size: 0.88rem; margin-bottom: 0.75rem; }}
        .meta {{ font-size: 0.82rem; color: var(--text-dim); }}
        .meta div {{ margin-bottom: 0.2rem; }}
        .meta strong {{ color: var(--text); }}
        .tags {{ margin-top: 0.6rem; display: flex; flex-wrap: wrap; gap: 0.3rem; }}
        .tag {{
            display: inline-block;
            background: var(--surface2);
            color: var(--text-dim);
            padding: 0.15rem 0.5rem;
            border-radius: 0.5rem;
            font-size: 0.75rem;
        }}
        .id {{ font-size: 0.72rem; color: var(--text-dim); margin-top: 0.6rem; font-family: monospace; opacity: 0.6; }}
        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-dim);
            font-size: 0.82rem;
            border-top: 1px solid var(--surface2);
        }}
        @media (max-width: 600px) {{
            .card-grid {{ grid-template-columns: 1fr; }}
            .stats {{ gap: 1rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p class="subtitle">Dzaleka Metadata Standard — Digital Heritage Catalogue</p>
        <div class="stats">
            <div class="stat"><div class="num">{total}</div><div class="label">Records</div></div>
            <div class="stat"><div class="num">{len(type_counts)}</div><div class="label">Types</div></div>
            <div class="stat"><div class="num">{len(creators)}</div><div class="label">Contributors</div></div>
            <div class="stat"><div class="num">{len(languages)}</div><div class="label">Languages</div></div>
        </div>
        <div class="badges">{type_badges}</div>
    </header>
    <main>{type_sections}
    </main>
    <footer>
        Generated by DMS CLI on {datetime.now().strftime("%Y-%m-%d %H:%M")} ·
        <a href="https://github.com/Dzaleka-Connect/Dzaleka-Metadata-Standard" style="color: var(--accent);">Dzaleka Metadata Standard</a>
    </footer>
</body>
</html>
"""
