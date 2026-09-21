import { useEffect, useState, useDeferredValue, useRef } from 'react';
import { Button } from '@cloudflare/kumo/components/button';
import { Input } from '@cloudflare/kumo/components/input';
import { Select } from '@cloudflare/kumo/components/select';
import { Badge } from '@cloudflare/kumo/components/badge';
import { api } from './records.js';

export default function Sources({ onImport }) {
  const [collections, setCollections] = useState([]);
  const [collection, setCollection] = useState('artworks');
  const [items, setItems] = useState(null);
  const [query, setQuery] = useState('');
  const search = useDeferredValue(query.toLowerCase());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [cached, setCached] = useState(false);
  const request = useRef(null);
  useEffect(() => {
    const controller = new AbortController();
    api('/api/sources', undefined, controller.signal).then(data => setCollections(data.collections))
      .catch(error => { if (error.name !== 'AbortError') setError(error.message); });
    return () => { controller.abort(); request.current?.abort(); };
  }, []);
  async function load(id) {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true); setError('');
    try {
      const result = await api(`/api/sources/${collection}${id ? `?id=${encodeURIComponent(id)}` : ''}`, undefined, controller.signal);
      if (id) onImport(result.draft);
      else { setItems(result.items); setCached(result.cached); }
    } catch (error) {
      if (error.name === 'AbortError') return;
      setError(error.message + (error.retryAfter ? ` Retry in ${error.retryAfter} seconds.` : ''));
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  const filtered = items?.filter(item => [item.title, item.description, item.creator, ...item.tags].join(' ').toLowerCase().includes(search));
  return <>
    <div className="page-heading"><div><p className="eyebrow">From the community</p><h1>Sources</h1><p>Start a DMS record from a published Dzaleka Services item.</p></div>
      <div className="actions">
        <a href="https://services.dzaleka.com/api-docs/" target="_blank" rel="noreferrer">API documentation &nearr;</a>
        <a href="https://services.dzaleka.com/encyclopedia/developers/" target="_blank" rel="noreferrer">Encyclopedia API &nearr;</a>
      </div></div>
    <div className="notice"><strong>Import as a draft, not as permission.</strong> Check the description, language, consent, and reuse rights before saving. Your local records are never sent to this service.</div>
    <div className="toolbar"><Select label="Source collection" disabled={busy} value={collection}
      items={Object.fromEntries(collections.map(item => [item.id, item.label]))}
      onValueChange={value => { setCollection(value || 'artworks'); setItems(null); setQuery(''); setError(''); }} />
      <Button variant="primary" disabled={busy} onClick={() => load()}>{busy ? 'Loading...' : items ? 'Reload collection' : 'Load collection'}</Button>
      <Input label="Search loaded items" value={query} disabled={!items} onChange={event => setQuery(event.target.value)} />
    </div>
    {error && <div className="notice error" role="alert">{error}</div>}
    {items === null ? <div className="empty-state"><h2>Choose what to explore</h2><p>Browse encyclopedia entries, art, photographs, events, stories, poets, services, or mapped places.</p><p className="muted">Connects only when you load a collection. Responses are cached for five minutes.</p></div> : <>
      <p className="list-caption" role="status">{filtered.length} of {items.length} items {cached && <Badge variant="secondary">Cached</Badge>}</p>
      <div className="source-grid">{filtered.map(item => <article className="source-card" key={item.identifier}>
        <div className="source-top"><Badge variant="secondary">{item.type}</Badge><a href={item.url} target="_blank" rel="noreferrer">Source &nearr;</a></div>
        <h2>{item.title}</h2><p className="source-description">{item.description || 'No description provided. Add context when reviewing the draft.'}</p>
        <p className="muted">{[item.creator, item.location, item.source_date].filter(Boolean).join(' / ') || 'Creator and date not recorded'}</p>
        <Button variant="secondary" disabled={busy} onClick={() => load(item.identifier)}>Create draft</Button>
      </article>)}</div>
      {!filtered.length && <div className="empty-state"><h2>No matching items</h2><p>Try another search or collection.</p></div>}
    </>}
  </>;
}
