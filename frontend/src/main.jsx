import React, { useState, useEffect, useEffectEvent, useDeferredValue } from 'react';
import { createRoot } from 'react-dom/client';
import { Button } from '@cloudflare/kumo/components/button';
import { Input } from '@cloudflare/kumo/components/input';
import { Select } from '@cloudflare/kumo/components/select';
import { Badge } from '@cloudflare/kumo/components/badge';
import { Dialog } from '@cloudflare/kumo/components/dialog';
import { HouseIcon, FilesIcon, PencilSimpleIcon, TreeStructureIcon, GlobeHemisphereEastIcon, PlusIcon } from '@phosphor-icons/react';
import '@cloudflare/kumo/styles/standalone';
import './styles.css';
import Editor from './Editor.jsx';
import Vocabulary from './Vocabulary.jsx';
import Sources from './Sources.jsx';
import { api, newRecord, cleanRecord, setField, addTerm, download, label } from './records.js';

const navigation = [['overview', 'Overview', HouseIcon], ['records', 'Records', FilesIcon],
  ['editor', 'Editor', PencilSimpleIcon], ['vocabulary', 'Vocabulary', TreeStructureIcon], ['sources', 'Sources', GlobeHemisphereEastIcon]];

function Records({ records, types, onEdit, onPreview, onNew }) {
  const [query, setQuery] = useState('');
  const search = useDeferredValue(query.toLowerCase());
  const [type, setType] = useState('');
  const visible = records.filter(record => (!type || record.type === type) &&
    [record.title, record.description, ...(record.subject || []), ...(record.creator || []).map(creator => creator.name)].join(' ').toLowerCase().includes(search));
  return <><div className="toolbar"><Input label="Search records" placeholder="Title, creator, or keyword" value={query} onChange={event => setQuery(event.target.value)} />
    <Select label="Record type" value={type} items={{ '': 'All types', ...Object.fromEntries(types.map(type => [type, label(type)])) }} onValueChange={value => setType(value || '')} />
  </div><p className="list-caption">{visible.length} of {records.length} records</p>
    {visible.length ? <div className="table-scroll"><table><thead><tr><th>Title</th><th>Type</th><th>Language</th><th>Access</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>
      {visible.map((record, i) => <tr key={record._file || `${record.id}-${i}`}><td><button className="record-title" onClick={() => onPreview(record)}>{record.title || 'Untitled record'}</button>
        <p className="muted">{record.creator?.map(creator => creator.name).join(', ') || 'Creator not recorded'}</p></td>
        <td><Badge variant="secondary">{record.type || 'Not set'}</Badge></td><td>{record.language || 'Not set'}</td>
        <td>{record.rights?.access_level || 'Not set'}</td><td><Button variant="secondary" onClick={() => onEdit(record)}>Edit<span className="sr-only"> {record.title}</span></Button></td></tr>)}
    </tbody></table></div> : <div className="empty-state"><h2>{records.length ? 'No matching records' : 'Your collection starts here'}</h2>
      <p>{records.length ? 'Try another keyword or record type.' : 'Describe a story, a place, or an object worth remembering.'}</p>
      {!records.length && <Button variant="primary" onClick={onNew}>Create a record</Button>}</div>}
  </>;
}

function App() {
  const [page, setPage] = useState('overview');
  const [info, setInfo] = useState(null);
  const [records, setRecords] = useState([]);
  const [record, setRecord] = useState(null);
  const [editing, setEditing] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [errors, setErrors] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);
  const [previewFeedback, setPreviewFeedback] = useState('');
  const [pending, setPending] = useState(null);
  const [retry, setRetry] = useState(0);
  const onUnload = useEffectEvent(event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
  useEffect(() => { window.addEventListener('beforeunload', onUnload); return () => window.removeEventListener('beforeunload', onUnload); }, []);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const data = await api('/api/schema', undefined, controller.signal);
        const saved = await api('/api/records', undefined, controller.signal);
        setInfo(data); setRecords(saved); setRecord(newRecord(data.version)); setNotice(null);
      } catch (error) { if (error.name !== 'AbortError') setNotice({ error: true, message: error.message }); }
    }
    load();
    return () => controller.abort();
  }, [retry]);
  function message(text, error = false) { setNotice({ message: text, error }); }
  function changePage(page) { setPage(page); setNotice(null); window.scrollTo(0, 0); }
  function replaceDraft(next, isEditing = false, source = false) {
    const action = () => {
      setRecord(cleanRecord(next)); setEditing(isEditing); setDirty(source);
      setErrors([]); setWarnings([]); changePage('editor');
      if (source) message('Draft imported. Review missing fields, consent, and reuse rights before saving.');
    };
    if (dirty) setPending(() => action); else action();
  }
  function create() { replaceDraft(newRecord(info.version)); }
  async function edit(record) {
    try {
      const result = await api('/api/validate', cleanRecord(record));
      if (!result.valid) { message('This record needs repair before it can be edited: ' + result.errors.map(error => `${error.field}: ${error.message}`).join(' '), true); return; }
      replaceDraft(record, true);
    } catch (error) { message(error.message, true); }
  }
  function update(path, value) { setRecord(record => setField(record, path, value)); setDirty(true); setErrors([]); setWarnings([]); setNotice(null); }
  async function validate(save = false) {
    setBusy(true); setNotice(null); setErrors([]); setWarnings([]);
    const next = cleanRecord(record);
    if (save) {
      const today = new Date().toISOString().slice(0, 10);
      next.date = { ...next.date, created: next.date?.created || today, ...(editing ? { modified: today } : {}) };
    }
    try {
      const result = await api('/api/validate', next);
      setErrors(result.errors); setWarnings(result.warnings);
      if (!result.valid) { window.scrollTo(0, 0); return; }
      if (!save) { message('Record is valid.' + (result.warnings.length ? ' Review the notes before sharing.' : '')); return; }
      const saved = await api('/api/save', next);
      setRecord(next); setDirty(false); setEditing(true); setWarnings(saved.warnings);
      message(`Saved locally as ${saved.file}.`);
      try { setRecords(await api('/api/records')); }
      catch { message('Record saved, but the collection could not refresh. Use Refresh records to reload it.', true); }
    } catch (error) { setErrors(error.details || []); message(error.message, true); }
    finally { setBusy(false); }
  }
  async function importFile(event) {
    const file = event.target.files?.[0]; event.target.value = '';
    if (!file) return;
    if (file.size > 1024 * 1024) { message('Choose a JSON record smaller than 1 MB.', true); return; }
    try {
      const data = JSON.parse(await file.text());
      if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Choose a single DMS JSON record, not a list.');
      const next = cleanRecord(data);
      const result = await api('/api/validate', next);
      if (!result.valid) throw new Error('Cannot import this record: ' + result.errors.map(error => `${error.field}: ${error.message}`).join(' '));
      replaceDraft(next, records.some(record => record.id === next.id), true);
    } catch (error) { message(error.message, true); }
  }
  async function exportLinked() {
    try { download(await api('/api/export-jsonld', preview), `dms-${preview.id}.jsonld`, 'application/ld+json'); }
    catch (error) { setPreviewFeedback(error.message); }
  }
  if (!info || !record) return <main className="boot"><h1>Dzaleka Metadata Standard</h1><p role="status">{notice?.message || 'Opening your workspace...'}</p>
    {notice && <Button variant="primary" onClick={() => { setNotice(null); setRetry(retry + 1); }}>Try again</Button>}</main>;
  const reviewCount = records.filter(record => !record.rights?.consent_status || ['pending', 'unknown', 'withheld'].includes(record.rights.consent_status)).length;
  return <div className="app-shell"><a href="#main" className="skip-link">Skip to content</a>
    <aside className="sidebar"><a className="brand" href="#" onClick={event => { event.preventDefault(); changePage('overview'); }}><span className="brand-symbol" aria-hidden="true">D</span><span>DMS<small>Dzaleka Metadata Standard</small></span></a>
      <nav aria-label="Main navigation">{navigation.map(([id, title, Icon]) => <Button key={id} variant="ghost" className={`nav-button ${page === id ? 'active' : ''}`}
        disabled={busy} aria-current={page === id ? 'page' : undefined} onClick={() => changePage(id)}><Icon size={19} />{title}{id === 'editor' && dirty && <span className="draft-dot" aria-label="Unsaved changes" />}</Button>)}</nav>
      <div className="sidebar-note"><span className="local-indicator" />Local workspace<p>Your records stay on this computer.</p><small>Schema {info.version}</small></div></aside>
    <div className="workspace"><header className="topbar"><span>Community heritage / <strong>{navigation.find(([id]) => id === page)?.[1]}</strong></span><div className="actions">
      {dirty && <Badge variant="warning">Unsaved draft</Badge>}<label className="import-button">Import JSON<input type="file" disabled={busy} accept="application/json,.json" onChange={importFile} aria-label="Import JSON" /></label>
      <Button variant="primary" disabled={busy} onClick={create}><PlusIcon size={16} />New record</Button></div></header>
      <main id="main" className="main-content" tabIndex={-1}>
        {notice && <div className={`notice ${notice.error ? 'error' : ''}`} role={notice.error ? 'alert' : 'status'}>{notice.message}<Button variant="ghost" aria-label="Dismiss message" onClick={() => setNotice(null)}>Close</Button></div>}
        {page === 'overview' && <><section className="welcome"><div><p className="eyebrow">The Dzaleka collection</p><h1>Keep the story.<br />Keep the context.</h1><p>A workspace for describing the people, places, and creations that carry Dzaleka's heritage.</p><div className="actions">
          <Button variant="primary" onClick={create}>Create a record</Button><Button variant="secondary" onClick={() => changePage('sources')}>Explore sources</Button></div></div>
          <div className="heritage-mark" aria-hidden="true"><span /><span /><span /><span /><i>Dzaleka<br />Malawi</i></div></section>
          <section className="stats" aria-label="Collection summary"><div><span>{records.length}</span><p>Saved records</p></div><div><span>{new Set(records.map(record => record.type).filter(Boolean)).size}</span><p>Heritage types</p></div><div><span>{new Set(records.map(record => record.language).filter(Boolean)).size}</span><p>Languages</p></div><div><span>{reviewCount}</span><p>Consent to review</p></div></section>
          <section><div className="section-heading"><h2>Your collection</h2><Button variant="ghost" onClick={() => changePage('records')}>View all records</Button></div>
            <Records records={records.slice(0, 5)} types={info.types} onEdit={edit} onPreview={record => setPreview(cleanRecord(record))} onNew={create} /></section>
        </>}
        {page === 'records' && <><div className="page-heading"><div><p className="eyebrow">The local archive</p><h1>Records</h1><p>Find, review, and edit the descriptions in your collection.</p></div><Button variant="secondary" onClick={async () => {
          try { setRecords(await api('/api/records')); message('Records refreshed.'); } catch (error) { message(error.message, true); }
        }}>Refresh records</Button></div><Records records={records} types={info.types} onEdit={edit} onPreview={record => setPreview(cleanRecord(record))} onNew={create} /></>}
        {page === 'editor' && <Editor schema={info.schema} record={record} onChange={update} errors={errors} warnings={warnings} busy={busy} editing={editing}
          onSave={() => validate(true)} onValidate={() => validate()} onPreview={() => setPreview(cleanRecord(record))} onVocabulary={() => changePage('vocabulary')} />}
        {page === 'vocabulary' && <Vocabulary record={record} onEditor={() => changePage('editor')} onAdd={(term, scheme) => {
          const next = addTerm(record, term, scheme); if (next !== record) { setRecord(next); setDirty(true); message(`${term.label} added to the draft.`); }
        }} />}
        {page === 'sources' && <Sources onImport={draft => replaceDraft(draft, false, true)} />}
        <footer>DMS / Dzaleka Metadata Standard<span>Describe thoughtfully. Share with permission.</span></footer>
      </main>
    </div>
    <Dialog.Root open={!!preview} onOpenChange={open => { if (!open) { setPreview(null); setPreviewFeedback(''); } }}><Dialog size="xl" className="dms-dialog">
      <Dialog.Title>Record preview</Dialog.Title><Dialog.Description>This is the complete metadata record. Downloads do not save or publish it.</Dialog.Description>
      {previewFeedback && <p className="notice" role="status">{previewFeedback}</p>}
      <pre className="json-preview">{JSON.stringify(preview, null, 2)}</pre><div className="actions">
        <Button variant="secondary" onClick={() => download(preview, `dms-${preview.id}.json`)}>Download JSON</Button>
        <Button variant="secondary" onClick={exportLinked}>Download JSON-LD</Button>
        <Button variant="secondary" onClick={async () => { try { await navigator.clipboard.writeText(JSON.stringify(preview, null, 2)); setPreviewFeedback('JSON copied.'); } catch { setPreviewFeedback('Copy is unavailable. Use Download JSON instead.'); } }}>Copy JSON</Button>
        <Button variant="primary" onClick={() => { setPreview(null); setPreviewFeedback(''); }}>Close preview</Button>
      </div></Dialog></Dialog.Root>
    <Dialog.Root role="alertdialog" open={!!pending} onOpenChange={open => { if (!open) setPending(null); }}><Dialog className="dms-dialog" size="lg">
      <Dialog.Title>Replace the unsaved draft?</Dialog.Title><Dialog.Description>Your current changes have not been saved. Replacing the draft will discard them.</Dialog.Description>
      <div className="actions"><Button variant="secondary" onClick={() => setPending(null)}>Keep editing</Button><Button variant="destructive" onClick={() => { pending(); setPending(null); }}>Replace draft</Button></div>
    </Dialog></Dialog.Root>
  </div>;
}

class ErrorBoundary extends React.Component {
  state = { error: false };
  static getDerivedStateFromError() { return { error: true }; }
  render() { return this.state.error ? <main className="boot"><h1>The workspace could not render</h1><p>Reload the page to try again. Unsaved changes may be lost.</p><Button onClick={() => location.reload()}>Reload workspace</Button></main> : this.props.children; }
}

createRoot(document.getElementById('root')).render(<ErrorBoundary><App /></ErrorBoundary>);
