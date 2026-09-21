import { useState, useEffect, useDeferredValue } from 'react';
import { Button } from '@cloudflare/kumo/components/button';
import { Input } from '@cloudflare/kumo/components/input';
import { Select } from '@cloudflare/kumo/components/select';
import { Badge } from '@cloudflare/kumo/components/badge';
import { Checkbox } from '@cloudflare/kumo/components/checkbox';
import { api, label } from './records.js';

export default function Vocabulary({ record, onAdd, onEditor }) {
  const [vocabularies, setVocabularies] = useState([]);
  const [vocabulary, setVocabulary] = useState('types');
  const [taxonomy, setTaxonomy] = useState(null);
  const [query, setQuery] = useState('');
  const search = useDeferredValue(query.toLowerCase());
  const [deprecated, setDeprecated] = useState(false);
  const [term, setTerm] = useState(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setTaxonomy(null); setTerm(null); setError('');
    async function load() {
      try {
        const catalog = await api('/api/taxonomy', undefined, controller.signal);
        setVocabularies(catalog.vocabularies);
        const data = await api(`/api/taxonomy/${vocabulary}`, undefined, controller.signal);
        setTaxonomy(data);
      } catch (error) { if (error.name !== 'AbortError') setError(error.message); }
    }
    load();
    return () => controller.abort();
  }, [vocabulary, retry]);
  const terms = taxonomy ? [...taxonomy.hasTopConcept, ...(deprecated ? taxonomy.deprecated || [] : [])]
    .filter(term => [term.id, term.label, term.definition, ...(term.altLabel || [])].join(' ').toLowerCase().includes(search)) : [];
  const base = `/api/taxonomy/${vocabulary}`;
  const exportPath = term ? `${base}/terms/${encodeURIComponent(term.id)}` :
    `${base}/terms?q=${encodeURIComponent(query)}&include_deprecated=${deprecated}`;
  const formats = [['json', 'JSON'], ['jsonld', 'JSON-LD'], ['ttl', 'Turtle'], ['rdfxml', 'RDF/XML'], ...(term ? [['html', 'HTML']] : [])];
  const added = record.subject_ref?.some(ref => ref.identifier === term?.id);
  return <>
    <div className="page-heading"><div><p className="eyebrow">A shared language</p><h1>Vocabulary</h1><p>Find terms, inspect their meaning, and keep references consistent.</p></div>
      <Button variant="secondary" onClick={onEditor}>Return to draft</Button></div>
    <div className="toolbar"><Select label="Vocabulary" value={vocabulary} items={Object.fromEntries(vocabularies.map(v => [v, label(v)]))}
      onValueChange={value => setVocabulary(value || 'types')} /><Input label="Find a term" value={query} onChange={event => setQuery(event.target.value)} />
      <Checkbox label="Include deprecated" checked={deprecated} onCheckedChange={setDeprecated} />
    </div>
    {error && <div className="notice error" role="alert">{error} <Button variant="secondary" onClick={() => setRetry(retry + 1)}>Try again</Button></div>}
    {!taxonomy && !error && <p role="status">Loading vocabulary...</p>}
    {taxonomy && <><div className="split-panel"><section className="term-list" aria-label="Terms"><div className="list-caption">{terms.length} terms</div>
      {terms.map(item => <button className={`term-button ${term?.id === item.id ? 'selected' : ''}`} key={item.id} onClick={() => setTerm(item)}>
        <span>{item.label}</span>{item.deprecated ? <Badge variant="warning">Deprecated</Badge> : <span aria-hidden="true">&rarr;</span>}
      </button>)}
      {!terms.length && <p className="empty-small">No matching terms. Try a different word.</p>}
    </section><section className="term-detail" aria-label="Term details">
      {term ? <><Badge variant={term.deprecated ? 'warning' : 'secondary'}>{term.deprecated ? 'Deprecated term' : 'Preferred term'}</Badge>
        <h2>{term.label}</h2><code>{term.id}</code><p>{term.definition || 'No definition recorded.'}</p>
        {!!term.altLabel?.length && <p><strong>Also known as:</strong> {term.altLabel.join(', ')}</p>}
        {['note', 'history', 'mapping', 'broader', 'related', 'supersededBy'].map(key => term[key] && <p key={key}><strong>{label(key)}:</strong> {Array.isArray(term[key]) ? term[key].join(', ') : term[key]}</p>)}
        <Button variant="primary" disabled={!!term.deprecated || added} onClick={() => onAdd(term, taxonomy.label)}>
          {added ? 'Added to draft' : term.deprecated ? 'Use the replacement term' : 'Add reference to draft'}
        </Button>
        <p className="muted">Adds a vocabulary reference, not a change to the record type or permissions.</p>
      </> : <><h2>{taxonomy.label}</h2><p>{taxonomy.definition}</p><p className="muted">Select a term to see its definition and references.</p></>}
      <div className="export-links"><span>{term ? 'Open this term' : 'Open filtered terms'}</span>{formats.map(([format, title]) => <a key={format}
        href={`${exportPath}${exportPath.includes('?') ? '&' : '?'}format=${format}`} target="_blank" rel="noreferrer">{title}</a>)}</div>
    </section></div><section className="technical-links"><h2>Taxonomy details</h2><div className="actions">
      <a href={`${base}?format=jsonld`} target="_blank" rel="noreferrer">Full vocabulary</a>
      <a href={`${base}/deprecated`} target="_blank" rel="noreferrer">Deprecated terms</a>
      <a href={`${base}/changes${term ? `?term=${encodeURIComponent(term.id)}` : ''}`} target="_blank" rel="noreferrer">{term ? 'Term change log' : 'Change log'}</a>
      <a href={`${base}/structure`} target="_blank" rel="noreferrer">Structure</a>
    </div></section></>}
  </>;
}
