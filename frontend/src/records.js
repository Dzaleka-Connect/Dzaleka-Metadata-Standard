export const label = (key) => ({
  id: 'Record ID', schema_version: 'Schema version', subject: 'Keywords',
  subject_ref: 'Vocabulary references', relation: 'Related record IDs',
  relation_detail: 'Typed relationships', file_uri: 'File URI', format: 'MIME type',
  language: 'Language code', creator: 'Creators', technical: 'Digital file',
}[key] || key.replaceAll('_', ' ').replace(/^./, c => c.toUpperCase()));

export function newRecord(version, id = crypto.randomUUID()) {
  return { id, title: '', description: '', type: 'story', language: 'en', schema_version: version };
}

export function reviewGaps(record) {
  const gaps = [];
  if (!String(record?.language || '').trim()) gaps.push('Language is not recorded.');
  if (!String(record?.description || '').trim()) gaps.push('Description is empty.');
  const consent = record?.rights?.consent_status;
  if (!consent || ['unknown', 'pending', 'withheld'].includes(consent)) {
    gaps.push(`Consent status is ${consent || 'unknown'}.`);
  }
  return gaps;
}

export function cleanRecord(record) {
  return Object.fromEntries(Object.entries(record).filter(([key]) => !key.startsWith('_')));
}

// Remove only the field being cleared, preserving zero values and unrelated metadata.
export function setField(record, path, value) {
  const next = structuredClone(record);
  function update(parent, index) {
    const key = path[index];
    if (index === path.length - 1) {
      if (value === '' || value === undefined || (Array.isArray(value) && !value.length)) delete parent[key];
      else parent[key] = value;
    } else {
      parent[key] ??= typeof path[index + 1] === 'number' ? [] : {};
      update(parent[key], index + 1);
      if (!Array.isArray(parent) && !Array.isArray(parent[key]) && Object.keys(parent[key]).length === 0) delete parent[key];
    }
  }
  update(next, 0);
  return next;
}

export function addTerm(record, term, scheme) {
  if (term.deprecated || record.subject_ref?.some(ref => ref.identifier === term.id)) return record;
  return { ...record, subject_ref: [...(record.subject_ref || []), {
    identifier: term.id, label: term.label, scheme,
  }] };
}

export async function api(path, body, signal) {
  const response = await fetch(path, {
    signal, ...(body === undefined ? {} : {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),
  });
  let data;
  try { data = await response.json(); }
  catch { throw new Error('The server returned an unreadable response. Please try again.'); }
  if (!response.ok) {
    const error = new Error(data.error || `Request failed (${response.status}).`);
    error.details = data.errors;
    error.retryAfter = data.retry_after;
    throw error;
  }
  return data;
}

export function download(data, filename, type = 'application/json') {
  const blob = new Blob([typeof data === 'string' ? data : JSON.stringify(data, null, 2) + '\n'], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
