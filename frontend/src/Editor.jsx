import { Button } from '@cloudflare/kumo/components/button';
import { Input, InputArea } from '@cloudflare/kumo/components/input';
import { Select } from '@cloudflare/kumo/components/select';
import { TagInput } from '@cloudflare/kumo/components/tag-input';
import { Checkbox } from '@cloudflare/kumo/components/checkbox';
import { label } from './records.js';

export const sections = [
  ['Description', ['title', 'type', 'description', 'language', 'subject']],
  ['People and dates', ['creator', 'date', 'coverage']],
  ['Place', ['location']],
  ['Rights and consent', ['rights']],
  ['Source and digital file', ['source', 'format', 'technical']],
  ['Connections', ['subject_ref', 'relation', 'relation_detail']],
  ['Record identity', ['id', 'schema_version']],
];

function Field({ definition, schema, value, path, onChange, errors, required = false }) {
  const spec = definition.$ref ? { ...schema.$defs[definition.$ref.split('/').pop()], ...definition } : definition;
  const key = path.at(-1);
  const name = label(key);
  const id = path.join('.');
  const error = errors.find(error => error.path === id)?.message;
  const shared = { label: name, required, error, id };
  if (spec.type === 'object') {
    return <fieldset className="field-object"><legend>{name}</legend><div className="field-grid">
      {Object.entries(spec.properties).map(([key, definition]) => <Field key={key} {...{
        definition, schema, value: value?.[key], path: [...path, key], onChange, errors,
        required: spec.required?.includes(key),
      }} />)}
    </div></fieldset>;
  }
  if (spec.type === 'array') {
    const items = spec.items.$ref ? schema.$defs[spec.items.$ref.split('/').pop()] : spec.items;
    const values = Array.isArray(value) ? value : [];
    if (items.enum) return <fieldset className="field-object"><legend>{name}</legend><div className="check-grid">
      {items.enum.map(item => <Checkbox key={item} label={label(item)} checked={values.includes(item)}
        onCheckedChange={checked => onChange(path, checked ? [...values, item] : values.filter(v => v !== item))} />)}
    </div></fieldset>;
    if (items.type === 'string') return <div className="field-wide"><TagInput {...shared} value={values}
      description="Press Enter after each value." onValueChange={items => onChange(path, items)} /></div>;
    return <fieldset className="field-object"><legend>{name}</legend>
      {values.map((item, i) => <div className="repeat-row" key={i}>
        <div className="field-grid">{Object.entries(items.properties).map(([key, definition]) => <Field key={key} {...{
          definition, schema, value: item[key], path: [...path, i, key], onChange, errors,
          required: items.required?.includes(key),
        }} />)}</div>
        <Button variant="ghost" onClick={() => onChange(path, values.filter((_, j) => j !== i))}>Remove {name.toLowerCase()} {i + 1}</Button>
      </div>)}
      <Button variant="secondary" onClick={() => onChange(path, [...values, {}])}>Add {name.toLowerCase()}</Button>
      {error && <p className="field-error">{error}</p>}
    </fieldset>;
  }
  if (spec.enum) return <Select {...shared} value={value ?? ''} className="full-width"
    items={Object.fromEntries([['', 'Not set'], ...spec.enum.map(value => [value, label(value)])])}
    onValueChange={value => onChange(path, value ?? '')} />;
  const long = ['description', 'access_note', 'note'].includes(key);
  if (long) return <div className="field-wide"><InputArea {...shared} value={value ?? ''} rows={key === 'description' ? 5 : 3}
    onChange={event => onChange(path, event.target.value)} /></div>;
  const numeric = spec.type === 'number' || spec.type === 'integer';
  return <Input {...shared} value={value ?? ''} readOnly={key === 'id' || key === 'schema_version'}
    type={numeric ? 'number' : spec.format === 'date' ? 'date' : 'text'}
    min={spec.minimum} max={spec.maximum} step={spec.type === 'integer' ? 1 : numeric ? 'any' : undefined}
    maxLength={spec.maxLength} description={key === 'language' ? 'For example: en, sw, fr, rw.' : undefined}
    onChange={event => onChange(path, numeric && event.target.value !== '' ? Number(event.target.value) : event.target.value)} />;
}

export default function Editor({ schema, record, onChange, errors, warnings, busy, onSave, onValidate, onPreview, onVocabulary, editing }) {
  return <>
    <div className="page-heading"><div><p className="eyebrow">Describe with care</p><h1>{editing ? 'Edit record' : 'Create a record'}</h1>
      <p>Start with the description. Add people, places, and permissions as you learn more.</p></div>
      <Button variant="secondary" onClick={onPreview}>Preview JSON</Button>
    </div>
    {!!errors.length && <div className="notice error" role="alert"><strong>Check these fields before saving</strong><ul>
      {errors.map((error, i) => <li key={i}>{error.field}: {error.message}</li>)}
    </ul></div>}
    {!!warnings.length && <div className="notice warning" role="status"><strong>Review notes</strong><ul>
      {warnings.map((warning, i) => <li key={i}>{typeof warning === 'string' ? warning : warning.message}</li>)}
    </ul></div>}
    <div className="editor-layout"><aside className="editor-index"><p>On this record</p>{sections.map(([name], i) => <a href={`#section-${i}`} key={name}>{name}</a>)}</aside>
      <div className="editor-fields"><fieldset disabled={busy}>
        {sections.map(([name, keys], i) => <section className="form-section" id={`section-${i}`} key={name}>
          <div className="section-heading"><h2>{name}</h2><span>{i === 0 ? 'Start here' : name === 'Record identity' ? 'Managed by DMS' : 'Optional'}</span></div>
          {name === 'Rights and consent' && <p className="section-note">A public source does not establish consent. These fields describe permissions; they do not enforce access to files.</p>}
          {name === 'Connections' && <Button variant="secondary" onClick={onVocabulary}>Browse vocabulary</Button>}
          <div className="field-grid">{keys.filter(key => schema.properties[key]).map(key => <Field key={key}
            definition={schema.properties[key]} schema={schema} value={record[key]} path={[key]} onChange={onChange}
            errors={errors} required={schema.required.includes(key)} />)}</div>
        </section>)}
      </fieldset><div className="save-bar"><span>Saved locally. Nothing is published.</span><div className="actions">
        <Button variant="secondary" disabled={busy} onClick={onValidate}>Validate</Button>
        <Button variant="primary" disabled={busy} onClick={onSave}>{busy ? 'Working...' : 'Save record'}</Button>
      </div></div></div>
    </div>
  </>;
}
