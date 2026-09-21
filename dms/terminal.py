"""Keyboard-first, read-only terminal workspace. Requires the optional tui extra."""

import asyncio
import json
from pathlib import Path

from rich.console import Group
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Resize
from textual.screen import ModalScreen, Screen
from textual.theme import Theme
from textual.widgets import Button, DataTable, Footer, Input, Select, Static, TabbedContent, TabPane

from dms import __schema_version__, __version__
from dms.schema import get_type_enum, load_schema
from dms.taxonomy import get_term_info, get_terms, get_vocabulary_list, load_taxonomy
from dms.services import ServicesClient, ServicesError, collection_list, source_to_draft
from dms.terminal_data import (
    RecordEntry,
    collection_counts,
    compact_path,
    display_text,
    read_collection,
    resolve_schema_field,
)

SEARCH_HINT = {
    "records": "Search titles, people, tags...",
    "vocabulary": "Search labels, IDs, definitions...",
    "schema": "Search field names and descriptions...",
    "sources": "Search loaded source titles...",
}

PAGE_COPY = {
    "records": ("Records", "Local descriptions, with their context intact."),
    "review": ("Needs review", "Schema errors and review notes."),
    "vocabulary": ("Vocabulary", "Shared terms, stable identifiers, and recorded changes."),
    "schema": ("Schema", f"DMS {__schema_version__}. Field definitions and constraints."),
    "sources": ("Sources", "Published Dzaleka Services items. Ctrl+R loads the selected collection."),
}

STATUS_STYLE = {"Invalid": "red", "Review": "yellow", "Valid": "green"}


class ComposerInput(Input):
    """Search field that lights the prompt chrome while it has focus."""

    def on_focus(self) -> None:
        if self.parent is not None:
            self.parent.set_class(True, "active")

    def on_blur(self) -> None:
        if self.parent is not None:
            self.parent.set_class(False, "active")


class HelpScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static("DMS terminal workspace", classes="dialog-title")
            with VerticalScroll():
                table = Table.grid(padding=(0, 2))
                for key, action in [
                    ("/", "Focus the search prompt"),
                    ("j / k  or  Up / Down", "Move through the list"),
                    ("Tab / Shift+Tab", "Move between controls"),
                    ("Ctrl+P", "Open the command palette"),
                    ("Ctrl+1 … 5", "Records / Review / Vocabulary / Schema / Sources"),
                    ("Ctrl+J", "View selected JSON"),
                    ("Ctrl+E", "View validation or term history"),
                    ("Ctrl+O", "View the overview"),
                    ("Y", "Copy selected JSON"),
                    ("G / g", "Jump to the last or first row"),
                    ("Ctrl+R", "Reload local records, or load the selected source"),
                    ("Ctrl+T", "Toggle light and dark themes"),
                    ("Escape", "Clear search, then return to the list"),
                    ("Q / Ctrl+Q", "Quit"),
                ]:
                    table.add_row(Text(key, style="bold"), Text(action))
                yield Static(table)
                yield Static(
                    "\nLocal records are never changed or uploaded. Sources are read only when you press Ctrl+R.\n"
                    "Use dms web to import a source as a draft, dms init to create records, or dms export for JSON-LD.",
                    markup=False,
                )
            yield Button("Return to workspace", id="close-help", variant="primary")

    @on(Button.Pressed, "#close-help")
    def close_help(self) -> None:
        self.dismiss()


class DMSApp(App):
    TITLE = "DMS"
    SUB_TITLE = "Dzaleka Metadata Standard"
    CSS_PATH = "terminal.tcss"
    COMMAND_PALETTE_BINDING = "ctrl+p"
    BINDINGS = [
        Binding("/", "search", "Search"),
        Binding("ctrl+p", "command_palette", "Commands", priority=True, show=False),
        Binding("ctrl+r", "reload", "Reload"),
        Binding("ctrl+j", "json", "JSON"),
        Binding("ctrl+e", "checks", "Checks"),
        Binding("ctrl+o", "overview", "Overview", show=False),
        Binding("y", "copy_json", "Copy", show=False),
        Binding("ctrl+t", "toggle_theme", "Theme", show=False),
        Binding("f1", "help", "Help"),
        Binding("ctrl+period", "help", "Help", show=False),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit", show=False, priority=True),
        Binding("ctrl+1", "records", "Records", show=False),
        Binding("ctrl+2", "review", "Review", show=False),
        Binding("ctrl+3", "vocabulary", "Vocabulary", show=False),
        Binding("ctrl+4", "schema", "Schema", show=False),
        Binding("ctrl+5", "sources", "Sources", show=False),
        Binding("escape", "escape", "List", show=False),
        Binding("enter", "focus_inspector", show=False),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("g", "cursor_home", show=False),
        Binding("G", "cursor_end", show=False),
    ]

    def __init__(self, directory: str | Path = "records", light: bool = False):
        super().__init__()
        self.directory = Path(directory).expanduser().resolve()
        self.entries: list[RecordEntry] = []
        self.catalog: dict[str, object] = {}
        self.workspace_mode = "records"
        self.review_only = False
        self.loading_records = False
        self.load_error = ""
        self.ready = False
        self.syncing = False
        self.selected_key: str | None = None
        self.generation = 0
        self.source_items: list[dict] = []
        self.source_error = ""
        self.source_cached = False
        self.loading_sources = False
        self.source_generation = 0
        self.payload: object = None
        self._services: ServicesClient | None = None
        self._drafts: dict[str, dict] = {}
        self.schema = load_schema()
        for theme in (
            Theme(
                name="dms-night",
                primary="#c5d4a8",
                secondary="#8ea59d",
                accent="#d4a07a",
                foreground="#e8e8e6",
                background="#141414",
                surface="#1c1c1c",
                panel="#262626",
                success="#9dba8c",
                warning="#d4b07a",
                error="#e08b7e",
                dark=True,
                variables={"footer-key-foreground": "#c5d4a8", "footer-background": "#141414"},
            ),
            Theme(
                name="dms-day",
                primary="#46683d",
                secondary="#546c60",
                accent="#99512d",
                foreground="#242c29",
                background="#fbfbf8",
                surface="#f2f3ed",
                panel="#e6eada",
                success="#3c663b",
                warning="#946316",
                error="#a53932",
                dark=False,
                variables={"footer-key-foreground": "#46683d", "footer-background": "#fbfbf8"},
            ),
        ):
            self.register_theme(theme)
        self.theme = "dms-day" if light else "dms-night"

    def compose(self) -> ComposeResult:
        with Horizontal(id="topbar"):
            yield Static(compact_path(self.directory), id="path", markup=False)
            yield Static("local only", id="stats-line", markup=False)
        with Horizontal(id="workspace"):
            with Vertical(id="sidebar"):
                yield Static("Workspace", classes="side-label")
                yield Button("Records", id="nav-records", classes="nav active")
                yield Button("Needs review", id="nav-review", classes="nav")
                yield Button("Vocabulary", id="nav-vocabulary", classes="nav")
                yield Button("Schema", id="nav-schema", classes="nav")
                yield Button("Sources", id="nav-sources", classes="nav")
                yield Static("Read-only\nNo uploads.\nSources load on request.", id="privacy", markup=False)
            with Vertical(id="content"):
                with Horizontal(id="heading-row"):
                    yield Static("Records", id="page-title")
                    yield Select(
                        [("All types", "all"), *[(item.capitalize(), item) for item in get_type_enum()]],
                        value="all",
                        allow_blank=False,
                        id="category",
                    )
                yield Static("Local descriptions, with their context intact.", id="page-description", markup=False)
                with Horizontal(id="split"):
                    with Vertical(id="list-panel"):
                        yield Static("Reading collection...", id="list-caption", markup=False)
                        yield DataTable(id="items", cursor_type="row", zebra_stripes=False, show_row_labels=False)
                        yield Static("", id="empty", markup=False)
                    with Vertical(id="inspector"):
                        yield Static("Select a record", id="item-title", markup=False)
                        yield Static("", id="item-meta", markup=False)
                        with TabbedContent(id="details"):
                            with TabPane("Overview", id="overview"):
                                with VerticalScroll(id="overview-scroll"):
                                    yield Static("Select a row to inspect its metadata.", id="overview-content", markup=False)
                            with TabPane("JSON", id="json"):
                                with VerticalScroll(id="json-scroll"):
                                    yield Static("", id="json-content", markup=False)
                            with TabPane("Checks / history", id="checks"):
                                with VerticalScroll(id="checks-scroll"):
                                    yield Static("", id="checks-content", markup=False)
        with Horizontal(id="composer"):
            yield Static(")", id="prompt-mark", markup=False)
            yield ComposerInput(placeholder=SEARCH_HINT["records"], id="search")
            yield Static(f"DMS {__version__}  ·  local only", id="composer-meta", markup=False)
        yield Footer(compact=True, show_command_palette=True)

    def on_mount(self) -> None:
        self.ready = True
        self._apply_size_classes(self.size.width, self.size.height)
        self.action_reload()
        self.query_one("#items", DataTable).focus()

    def on_resize(self, event: Resize) -> None:
        self._apply_size_classes(event.size.width, event.size.height)

    def _apply_size_classes(self, width: int, height: int) -> None:
        self.set_class(width < 100, "compact")
        self.set_class(height < 32, "short")

    def get_system_commands(self, screen: Screen):
        yield from super().get_system_commands(screen)
        for title, help_text, callback in (
            ("Browse records", "Inspect the local collection", self.action_records),
            ("Review records", "Show records with errors or review notes", self.action_review),
            ("Browse vocabulary", "Find DMS terms, replacements, and history", self.action_vocabulary),
            ("Browse schema", "Read the fields and constraints", self.action_schema),
            ("Browse sources", "Read published Dzaleka Services collections", self.action_sources),
            ("Search this workspace", "Focus the prompt and filter the current list", self.action_search),
            ("Reload or load collection", "Read local files, or fetch the selected source", self.action_reload),
            ("Show JSON", "Inspect the selected item as JSON", self.action_json),
            ("Show checks and history", "Read validation results or term changes", self.action_checks),
            ("Copy JSON", "Copy the selected item JSON to the clipboard", self.action_copy_json),
            ("Toggle theme", "Switch between the night and day palettes", self.action_toggle_theme),
            ("Keyboard shortcuts", "Show navigation and other DMS commands", self.action_help),
        ):
            yield SystemCommand(title, help_text, callback)

    @work(exclusive=True, group="collection", exit_on_error=False)
    async def load_records(self, generation: int) -> None:
        try:
            entries = await asyncio.to_thread(read_collection, self.directory)
            error = ""
        except OSError as exc:
            entries, error = [], display_text(str(exc))
        if generation != self.generation:
            return
        self.entries, self.load_error = entries, error
        self.loading_records = False
        self._update_stats_line()
        if self.workspace_mode != "sources":
            self.refresh_list()
            if not error:
                self.notify(f"{len(entries)} local records")

    def _update_stats_line(self) -> None:
        if self.workspace_mode == "sources":
            if self.loading_sources:
                text = "Reading sources..."
            elif self.source_error:
                text = "Could not load source"
            elif not self.source_items:
                text = "Sources idle  ·  Ctrl+R to load"
            else:
                text = f"{len(self.source_items)} source items" + ("  ·  cached" if self.source_cached else "")
        elif self.loading_records:
            text = "Reading records..."
        elif self.load_error:
            text = "Could not read collection"
        else:
            total, valid, invalid, review = collection_counts(self.entries)
            text = f"{total} records  ·  {valid} valid  ·  {invalid} invalid  ·  {review} review"
        self.query_one("#stats-line", Static).update(text)

    def action_reload(self) -> None:
        if self.workspace_mode == "sources":
            self.source_generation += 1
            self.loading_sources = True
            self.source_error = ""
            self._update_stats_line()
            self.load_sources(self.source_generation)
            return
        self.generation += 1
        self.loading_records = True
        self._update_stats_line()
        self.load_records(self.generation)

    @work(exclusive=True, group="sources", exit_on_error=False)
    async def load_sources(self, generation: int) -> None:
        collection = str(self.query_one("#category", Select).value)
        if collection == "all":
            collections = collection_list()
            collection = collections[0]["id"] if collections else ""
            if collection:
                self.syncing = True
                self.query_one("#category", Select).value = collection
                self.syncing = False
        try:
            if self._services is None:
                self._services = ServicesClient()
            items, cached = await asyncio.to_thread(self._services.fetch, collection)
            error = ""
        except ServicesError as exc:
            items, cached, error = [], False, str(exc)
            if exc.retry_after:
                error += f" Retry in {exc.retry_after} seconds."
        if generation != self.source_generation:
            return
        self.source_items, self.source_cached, self.source_error = items, cached, error
        self.loading_sources = False
        self._drafts.clear()
        self._update_stats_line()
        if self.workspace_mode == "sources":
            self.refresh_list()
            if error:
                self.notify(error, severity="warning")
            else:
                self.notify(f"{len(items)} source items" + ("  ·  cached" if cached else ""))

    def switch_mode(self, mode: str, review: bool = False) -> None:
        self.workspace_mode, self.review_only, self.selected_key = mode, review, None
        self.syncing = True
        search = self.query_one("#search", Input)
        search.value = ""
        search.placeholder = SEARCH_HINT[mode]
        category = self.query_one("#category", Select)
        if mode == "records":
            options = [("All types", "all"), *[(item.capitalize(), item) for item in get_type_enum()]]
            selected = "all"
        elif mode == "sources":
            collections = collection_list()
            options = [(item["label"], item["id"]) for item in collections]
            selected = self.source_items[0]["collection"] if self.source_items else collections[0]["id"]
        else:
            options = [("All vocabularies", "all"), *[(item.replace("_", " ").capitalize(), item) for item in get_vocabulary_list()]]
            selected = "all"
        category.set_options(options)
        if options:
            category.value = selected
        category.display = mode != "schema"
        page = PAGE_COPY["review" if review else mode]
        self.query_one("#page-title", Static).update(page[0])
        self.query_one("#page-description", Static).update(page[1])
        for button in self.query(".nav"):
            button.set_class(button.id == f"nav-{'review' if review else mode}", "active")
        self.query_one("#details", TabbedContent).active = "overview"
        self.syncing = False
        self.query_one("#composer-meta", Static).update(
            f"DMS {__version__}  ·  " + ("Ctrl+R loads sources" if mode == "sources" else "local only")
        )
        self._update_stats_line()
        self.refresh_list()
        self.action_focus_list()

    def action_records(self) -> None:
        self.switch_mode("records")

    def action_review(self) -> None:
        self.switch_mode("records", review=True)

    def action_vocabulary(self) -> None:
        self.switch_mode("vocabulary")

    def action_schema(self) -> None:
        self.switch_mode("schema")

    def action_sources(self) -> None:
        self.switch_mode("sources")

    def action_toggle_theme(self) -> None:
        self.theme = "dms-day" if self.theme == "dms-night" else "dms-night"
        if self.selected_key and self.selected_key in self.catalog:
            self.show_item(self.selected_key)

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        actions = {
            "nav-records": self.action_records,
            "nav-review": self.action_review,
            "nav-vocabulary": self.action_vocabulary,
            "nav-schema": self.action_schema,
            "nav-sources": self.action_sources,
        }
        if event.button.id in actions:
            actions[event.button.id]()

    @on(Input.Changed, "#search")
    @on(Select.Changed, "#category")
    def filter_changed(self, event=None) -> None:
        if not self.ready or self.syncing:
            return
        if self.workspace_mode == "sources" and isinstance(event, Select.Changed):
            loaded = self.source_items[0]["collection"] if self.source_items else None
            if str(event.value) != loaded:
                self.source_items = []
                self.source_error = ""
                self.source_cached = False
                self.selected_key = None
                self._drafts.clear()
                self._update_stats_line()
        self.refresh_list()

    def refresh_list(self) -> None:
        table = self.query_one("#items", DataTable)
        table.clear(columns=True)
        self.catalog = {}
        query = self.query_one("#search", Input).value.strip().casefold()
        category = str(self.query_one("#category", Select).value)
        rows: list[tuple[str, object, list[Text]]] = []
        if self.workspace_mode == "records":
            table.add_columns("Record", "Type", "State")
            for entry in self.entries:
                if entry.matches(query, category, self.review_only):
                    record = entry.record or {}
                    rows.append((
                        entry.key,
                        entry,
                        [
                            Text(entry.title.replace("\n", " ")),
                            Text(display_text(record.get("type"), "-")),
                            Text(entry.status, style=STATUS_STYLE[entry.status]),
                        ],
                    ))
        elif self.workspace_mode == "sources":
            table.add_columns("Source", "Type", "Collection")
            for entry in self.source_items:
                haystack = " ".join([
                    display_text(entry.get("title"), ""),
                    display_text(entry.get("description"), ""),
                    display_text(entry.get("creator"), ""),
                    " ".join(entry.get("tags") or []),
                ]).casefold()
                if query and query not in haystack:
                    continue
                rows.append((
                    entry["identifier"],
                    entry,
                    [
                        Text(display_text(entry.get("title")).replace("\n", " ")),
                        Text(display_text(entry.get("type"), "-")),
                        Text(display_text(entry.get("collection_label"), entry.get("collection"))),
                    ],
                ))
        elif self.workspace_mode == "vocabulary":
            table.add_columns("Term", "Vocabulary", "State")
            for vocabulary in get_vocabulary_list():
                if category != "all" and vocabulary != category:
                    continue
                for term in get_terms(vocabulary, include_deprecated=True):
                    if query not in json.dumps(term, ensure_ascii=False).casefold():
                        continue
                    key = vocabulary + ":" + term["id"]
                    rows.append((
                        key,
                        (vocabulary, term),
                        [
                            Text(display_text(term.get("label"))),
                            Text(vocabulary.replace("_", " ")),
                            Text("Deprecated" if term.get("deprecated") else "Active"),
                        ],
                    ))
        else:
            table.add_columns("Field", "Type", "Required")
            for key in self.schema.get("properties", {}):
                definition = resolve_schema_field(self.schema, key)
                if query not in (key + json.dumps(definition)).casefold():
                    continue
                rows.append((
                    key,
                    definition,
                    [
                        Text(key),
                        Text(str(definition.get("type", "object"))),
                        Text("Yes" if key in self.schema.get("required", []) else "No"),
                    ],
                ))
        for key, item, cells in rows:
            self.catalog[key] = item
            table.add_row(*cells, key=key)
        if table.columns:
            first_column = next(iter(table.columns))
            table.columns[first_column].width = 22 if self.size.width >= 100 else 28
            table.columns[first_column].auto_width = False
        noun = {"schema": "fields", "vocabulary": "terms", "sources": "sources"}.get(self.workspace_mode, "entries")
        self.query_one("#list-caption", Static).update(f"{len(rows)} {noun}")
        table.display = bool(rows)
        empty = self.query_one("#empty", Static)
        empty.display = not rows
        if self.workspace_mode == "sources":
            empty.update(self.source_error or (
                "No matching items.\nClear the search." if query else
                "Press Ctrl+R to load this collection from services.dzaleka.com.\nNothing is uploaded. Reads are cached for five minutes."
            ))
        elif self.load_error:
            empty.update(self.load_error)
        elif query or category != "all" or self.review_only:
            empty.update("No matching items.\nClear the search or change the filter.")
        else:
            empty.update("No records yet.\n\nCreate one with dms init, then press Ctrl+R to reload.")
        if rows:
            keys = list(self.catalog)
            selected = self.selected_key if self.selected_key in self.catalog else keys[0]
            table.move_cursor(row=keys.index(selected))
            self.show_item(selected)
        else:
            self.selected_key = None
            self.query_one("#item-title", Static).update("No item selected")
            self.payload = None
            for element in ("item-meta", "overview-content", "json-content", "checks-content"):
                self.query_one(f"#{element}", Static).update("")

    @on(DataTable.RowHighlighted, "#items")
    def highlight_row(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None:
            return
        key = str(event.row_key.value)
        if key in self.catalog:
            self.show_item(key)

    def show_item(self, key: str) -> None:
        self.selected_key = key
        item = self.catalog[key]
        if isinstance(item, RecordEntry):
            title, meta, content, checks, payload = self._record_views(item)
        elif self.workspace_mode == "sources":
            title, meta, content, checks, payload = self._source_views(item)
        elif self.workspace_mode == "vocabulary":
            title, meta, content, checks, payload = self._vocabulary_views(item)
        else:
            title, meta, content, checks, payload = self._schema_views(key, item)
        self.payload = payload
        self.query_one("#item-title", Static).update(Text(title, style="bold"))
        self.query_one("#item-meta", Static).update(Text(meta))
        self.query_one("#overview-content", Static).update(Group(*content))
        self.query_one("#checks-content", Static).update(Group(*checks))
        syntax_theme = "github-dark" if self.current_theme.dark else "default"
        self.query_one("#json-content", Static).update(
            Syntax(
                json.dumps(payload, indent=2, ensure_ascii=False),
                "json",
                theme=syntax_theme,
                word_wrap=True,
                background_color="default",
            )
        )

    def _record_views(self, item: RecordEntry) -> tuple[str, str, list, list, dict]:
        record = item.record or {}
        title = item.title
        meta = f"{display_text(item.key)}  ·  {item.status}"
        content = [Text(display_text(record.get("description"), "No description recorded."))]
        fields = Table.grid(padding=(0, 2))
        fields.add_column(style="dim", width=12)
        fields.add_column(ratio=1)
        for label, value in (("Type", record.get("type")), ("Language", record.get("language")), ("Record ID", record.get("id"))):
            fields.add_row(Text(label), Text(display_text(value)))
        for section, keys in (
            ("location", ["name", "area"]),
            ("rights", ["access_level", "consent_status", "license"]),
            ("date", ["created", "event_date"]),
            ("source", ["collection", "contributor"]),
        ):
            values = record.get(section)
            if isinstance(values, dict):
                for field_name in keys:
                    if field_name in values:
                        fields.add_row(Text(field_name.replace("_", " ").capitalize()), Text(display_text(values[field_name])))
        creators = record.get("creator", [])
        if isinstance(creators, list) and creators:
            fields.add_row(
                Text("Creators"),
                Text(", ".join(display_text(value.get("name")) for value in creators if isinstance(value, dict))),
            )
        subjects = record.get("subject", [])
        if isinstance(subjects, list) and subjects:
            fields.add_row(Text("Keywords"), Text(", ".join(display_text(value) for value in subjects)))
        relations = record.get("relation_detail", [])
        if isinstance(relations, list) and relations:
            fields.add_row(
                Text("Relations"),
                Text("; ".join(
                    display_text(value.get("label") or value.get("target"))
                    for value in relations if isinstance(value, dict)
                )),
            )
        content.extend([Text("\nRecord details", style="bold"), fields])
        content.append(Text(f"\n{item.status}. {len(item.errors)} errors, {len(item.warnings)} review notes.", style="dim"))
        checks = [Text(f"{len(item.errors)} errors  ·  {len(item.warnings)} review notes", style="bold")]
        if not item.errors:
            checks.append(Text("\nPasses DMS schema and vocabulary validation."))
        checks.extend(Text(f"\n{display_text(error['field'])}\n{display_text(error['message'])}") for error in item.errors)
        checks.extend(Text(f"\nReview: {display_text(warning)}") for warning in item.warnings)
        payload = record if item.record is not None else {"file": item.key, "errors": item.errors}
        return title, meta, content, checks, payload

    def _source_views(self, item: dict) -> tuple[str, str, list, list, dict]:
        title = display_text(item.get("title"))
        meta = f"{display_text(item.get('collection_label'))}  ·  {display_text(item.get('type'))}"
        content = [Text(display_text(item.get("description"), "No description provided."))]
        fields = Table.grid(padding=(0, 2))
        fields.add_column(style="dim", width=12)
        fields.add_column(ratio=1)
        for label, key in (("Identifier", "identifier"), ("Creator", "creator"), ("Location", "location"), ("Date", "source_date"), ("License", "license")):
            if item.get(key):
                fields.add_row(Text(label), Text(display_text(item.get(key))))
        if item.get("tags"):
            fields.add_row(Text("Tags"), Text(", ".join(display_text(tag) for tag in item["tags"])))
        fields.add_row(Text("Source"), Text(display_text(item.get("url") or item.get("source_uri"))))
        content.extend([Text("\nSource details", style="bold"), fields])
        content.append(Text("\nDraft preview only. Import and review consent in dms web.", style="dim"))
        checks = [
            Text("This workspace does not save source drafts.", style="bold"),
            Text("\nCtrl+R loads the collection. Local records are never uploaded."),
        ]
        identifier = display_text(item.get("identifier"), title)
        payload = self._drafts.setdefault(identifier, source_to_draft(item))
        return title, meta, content, checks, payload

    def _vocabulary_views(self, item) -> tuple[str, str, list, list, dict]:
        vocabulary, term = item
        info = get_term_info(vocabulary, term["id"]) or {**term, "changeLog": []}
        title = display_text(term.get("label"))
        meta = display_text(term.get("id"))
        content = [Text(display_text(term.get("definition"))), Text("\n" + load_taxonomy(vocabulary)["label"], style="dim")]
        for field_name in ("altLabel", "note", "mapping", "broader", "related", "supersededBy"):
            value = term.get(field_name)
            if value:
                value = ", ".join(map(str, value)) if isinstance(value, list) else str(value)
                content.extend([Text("\n" + field_name, style="bold"), Text(display_text(value))])
        checks = [Text("Deprecated term. Use the recorded replacement." if term.get("deprecated") else "Active vocabulary term.", style="bold")]
        changes = info.get("changeLog") or []
        checks.extend(Text("\n" + display_text(change.get("message"))) for change in changes)
        if not changes:
            checks.append(Text("\nNo term-specific changes recorded."))
        return title, meta, content, checks, info

    def _schema_views(self, key: str, item: dict) -> tuple[str, str, list, list, dict]:
        required = key in self.schema.get("required", [])
        title, meta = key, "Required" if required else "Optional"
        content = [Text(display_text(item.get("description"))), Text("\nType: " + str(item.get("type", "object")))]
        for name in ("format", "enum", "pattern", "minLength", "maxLength", "const"):
            if name in item:
                content.append(Text("\n" + name + ": " + json.dumps(item[name], ensure_ascii=False)))
        checks = [Text("The JSON tab contains the complete field definition, including nested properties.")]
        return title, meta, content, checks, item

    def action_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_focus_list(self) -> None:
        self.query_one("#items", DataTable).focus()

    def action_escape(self) -> None:
        search = self.query_one("#search", Input)
        if self.focused is search:
            if search.value:
                search.value = ""
                return
            self.action_focus_list()
            return
        self.action_focus_list()

    def action_json(self) -> None:
        self.query_one("#details", TabbedContent).active = "json"
        self.query_one("#json-scroll", VerticalScroll).focus()

    def action_overview(self) -> None:
        self.query_one("#details", TabbedContent).active = "overview"
        self.query_one("#overview-scroll", VerticalScroll).focus()

    def action_checks(self) -> None:
        self.query_one("#details", TabbedContent).active = "checks"
        self.query_one("#checks-scroll", VerticalScroll).focus()

    def action_focus_inspector(self) -> None:
        tabs = self.query_one("#details", TabbedContent)
        scroll_id = {"json": "json-scroll", "checks": "checks-scroll"}.get(tabs.active, "overview-scroll")
        self.query_one("#" + scroll_id, VerticalScroll).focus()

    def action_copy_json(self) -> None:
        if isinstance(self.focused, Input) or self.payload is None:
            return
        self.copy_to_clipboard(json.dumps(self.payload, indent=2, ensure_ascii=False, default=str))
        self.notify("Copied JSON")

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_cursor_down(self) -> None:
        focused = self.focused
        if isinstance(focused, DataTable):
            focused.action_cursor_down()
        elif isinstance(focused, VerticalScroll):
            focused.scroll_down()

    def action_cursor_up(self) -> None:
        focused = self.focused
        if isinstance(focused, DataTable):
            focused.action_cursor_up()
        elif isinstance(focused, VerticalScroll):
            focused.scroll_up()

    def action_cursor_home(self) -> None:
        table = self.query_one("#items", DataTable)
        if table.row_count:
            table.move_cursor(row=0)
            table.focus()

    def action_cursor_end(self) -> None:
        table = self.query_one("#items", DataTable)
        if table.row_count:
            table.move_cursor(row=table.row_count - 1)
            table.focus()
