import { test } from 'node:test';
import assert from 'node:assert/strict';
import { newRecord, setField, cleanRecord, addTerm } from './records.js';

test('new records have stable explicit identity', () => {
  assert.equal(newRecord('1.1.0', 'known-id').id, 'known-id');
});

test('editing preserves zero values, nested fields, and the original object', () => {
  const record = { id: 'id', location: { name: 'Place', latitude: 0, longitude: 0 }, technical: { file_size_bytes: 0, checksum: 'abc' }, creator: [{ name: 'Amina', role: 'artist' }] };
  const next = setField(record, ['creator', 0, 'name'], 'Jean');
  assert.equal(record.creator[0].name, 'Amina');
  assert.equal(next.creator[0].role, 'artist');
  assert.deepEqual(next.location, record.location);
  assert.deepEqual(next.technical, record.technical);
});

test('clearing a field removes only that property and empty parents', () => {
  assert.deepEqual(setField({ location: { name: 'Place', latitude: 0 } }, ['location', 'latitude'], ''), { location: { name: 'Place' } });
  assert.deepEqual(setField({ technical: { checksum: 'abc' } }, ['technical', 'checksum'], ''), {});
  assert.deepEqual(setField({}, ['technical', 'file_size_bytes'], 0), { technical: { file_size_bytes: 0 } });
  assert.deepEqual(setField({ subject: ['art'] }, ['subject'], []), {});
});

test('internal filenames never leak into exported records', () => {
  assert.deepEqual(cleanRecord({ title: 'Title', _file: 'record.json', _other: true }), { title: 'Title' });
});

test('clearing an array item keeps an editable row rather than a sparse array', () => {
  assert.deepEqual(setField({ creator: [{ name: 'Amina' }] }, ['creator', 0, 'name'], ''), { creator: [{}] });
});

test('canonical references are deduplicated and deprecated terms cannot be added', () => {
  const term = { id: 'dms:type/story', label: 'Story' };
  const record = addTerm({}, term, 'Dzaleka Heritage Item Types');
  assert.equal(record.subject_ref[0].identifier, term.id);
  assert.strictEqual(addTerm(record, term, 'Dzaleka Heritage Item Types'), record);
  assert.deepEqual(addTerm({}, { ...term, deprecated: true }, 'Types'), {});
});
