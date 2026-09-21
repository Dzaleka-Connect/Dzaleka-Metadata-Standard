const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const { createInterface } = require('node:readline');
const { mkdir } = require('node:fs/promises');
const { existsSync } = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

async function main() {
  const root = path.resolve(__dirname, '../..');
  const localPython = path.join(root, '.venv/bin/python');
  const server = spawn(process.env.PYTHON || (existsSync(localPython) ? localPython : 'python3'), ['frontend/tests/serve.py'], {
    cwd: root, env: { ...process.env, PYTHONPATH: root }, stdio: ['ignore', 'pipe', 'pipe'],
  });
  let browser;
  let page;
  let stderr = '';
  server.stderr.on('data', chunk => { stderr += chunk; });
  const lines = createInterface({ input: server.stdout });
  const timer = setTimeout(() => server.kill('SIGINT'), 10000);
  const url = await new Promise((resolve, reject) => {
    server.on('error', reject);
    lines.on('line', line => { if (line.startsWith('http://')) resolve(line); });
    server.on('exit', () => reject(new Error('Test server stopped: ' + stderr)));
  });
  clearTimeout(timer);
  try {
    await mkdir(path.join(__dirname, '../test-results'), { recursive: true });
    browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined });
    page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    page.setDefaultTimeout(10000);
    const errors = [];
    const external = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error' && !message.text().includes('Failed to load resource')) errors.push(message.text()); });
    page.on('request', request => { if (!request.url().startsWith(url) && !request.url().startsWith('data:')) external.push(request.url()); });
    await page.goto(url);
    await page.getByRole('heading', { name: /Keep the story/ }).waitFor();
    await page.screenshot({ path: path.join(__dirname, '../test-results/desktop.png'), fullPage: true });
    await page.getByRole('button', { name: 'New record', exact: true }).click();
    await page.getByLabel('Title', { exact: true }).fill("Amina's story <script>alert(1)</script>");
    await page.getByLabel('Description', { exact: true }).fill('A community story, recorded with care.');
    await page.getByRole('group', { name: 'Location', exact: true }).getByLabel('Name', { exact: true }).fill('Dzaleka');
    await page.getByLabel(/^Latitude/).fill('0');
    await page.getByLabel(/^Longitude/).fill('0');
    await page.getByLabel(/^File size bytes/).fill('0');
    await page.getByRole('button', { name: 'Save record', exact: true }).click();
    await page.getByRole('status').filter({ hasText: 'Saved locally as' }).waitFor();
    let saved = await (await page.request.get(url + '/api/records')).json();
    assert.equal(saved.length, 1);
    assert.equal(saved[0].location.latitude, 0);
    assert.equal(saved[0].technical.file_size_bytes, 0);
    const id = saved[0].id;

    await page.getByRole('navigation').getByRole('button', { name: 'Vocabulary', exact: true }).click();
    await page.getByRole('button', { name: /^Story/ }).click();
    await page.getByRole('button', { name: 'Add reference to draft', exact: true }).click();
    assert(await page.getByRole('button', { name: 'Added to draft', exact: true }).isDisabled());
    await page.getByRole('checkbox', { name: 'Include deprecated', exact: true }).check();
    await page.getByRole('button', { name: /Image.*Deprecated/ }).click();
    assert(await page.getByRole('button', { name: 'Use the replacement term' }).isDisabled());
    await page.getByRole('button', { name: 'Return to draft' }).click();
    await page.getByRole('button', { name: 'Save record', exact: true }).click();
    await page.getByRole('status').filter({ hasText: 'Saved locally as' }).waitFor();
    saved = await (await page.request.get(url + '/api/records')).json();
    assert.equal(saved[0].subject_ref[0].identifier, 'dms:type/story');
    assert.equal(saved[0].id, id);
    await page.getByRole('navigation').getByRole('button', { name: 'Records', exact: true }).click();
    await page.getByRole('button', { name: /^Edit Amina/ }).click();
    assert.equal(await page.getByLabel(/^Latitude/).inputValue(), '0');
    await page.getByRole('combobox', { name: 'Type', exact: true }).click();
    await page.getByRole('option', { name: 'Photo', exact: true }).click();
    await page.getByRole('button', { name: 'Save record', exact: true }).click();
    await page.getByRole('status').filter({ hasText: 'Saved locally as' }).waitFor();
    saved = await (await page.request.get(url + '/api/records')).json();
    assert.equal(saved.length, 1);
    assert.equal(saved[0].type, 'photo');

    await page.getByRole('button', { name: 'Preview JSON' }).click();
    const downloadEvent = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download JSON', exact: true }).click();
    assert.equal((await downloadEvent).suggestedFilename(), `dms-${id}.json`);
    const linkedEvent = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download JSON-LD', exact: true }).click();
    assert.equal((await linkedEvent).suggestedFilename(), `dms-${id}.jsonld`);
    await page.getByRole('button', { name: 'Close preview' }).click();

    await page.getByLabel('Title', { exact: true }).fill('Unsaved change');
    await page.getByRole('button', { name: 'New record', exact: true }).click();
    await page.getByRole('alertdialog').waitFor();
    await page.getByRole('button', { name: 'Keep editing', exact: true }).click();
    assert.equal(await page.getByLabel('Title', { exact: true }).inputValue(), 'Unsaved change');
    await page.getByRole('button', { name: 'New record', exact: true }).click();
    await page.getByRole('button', { name: 'Replace draft', exact: true }).click();

    const imported = { id: 'df0202bc-788c-4551-8e6b-e3dc394ed544', title: 'Complete imported record', type: 'document', description: 'Full schema coverage.', language: 'sw',
      creator: [{ name: 'Amina', identifier: 'person-1', role: 'author', affiliation: 'Community' }],
      date: { created: '2024-01-02', event_date: '2020-03-04' }, coverage: { start_date: '2020-01-01', end_date: '2020-12-31', period: '2020' },
      location: { name: 'Dzaleka', identifier: 'place-1', area: 'Market', latitude: 0, longitude: 0 },
      rights: { license: 'CC-BY-4.0', access_level: 'restricted', consent_status: 'pending', sensitivity: ['personal-data'], access_note: 'Review', holder: 'Amina' },
      source: { contributor: 'Amina', collection: 'Stories', collection_identifier: 'collection-1', original_format: 'Notebook' },
      format: 'application/pdf', technical: { file_uri: 'https://example.com/record.pdf', filename: 'record.pdf', checksum: 'abc', checksum_algorithm: 'sha256', file_size_bytes: 0, duration_seconds: 0, page_count: 3, width_px: 400, height_px: 600 },
      subject: ['community'], subject_ref: [{ identifier: 'https://example.com/concept', label: 'Community', scheme: 'Local' }], relation: [id],
      relation_detail: [{ target: id, relation_type: 'references', label: 'Story', note: 'Source context' }], schema_version: '1.1.0' };
    await page.getByLabel('Import JSON', { exact: true }).setInputFiles({ name: 'record.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(imported)) });
    await page.getByLabel('Title', { exact: true }).filter({ visible: true }).waitFor();
    await page.waitForFunction(() => document.getElementById('title')?.value === 'Complete imported record');
    await page.getByRole('button', { name: 'Save record', exact: true }).click();
    await page.getByRole('status').filter({ hasText: 'Saved locally as' }).waitFor();
    saved = await (await page.request.get(url + '/api/records')).json();
    const roundTrip = saved.find(record => record.id === imported.id);
    delete roundTrip._file;
    assert.deepEqual(roundTrip, imported);

    let sourceCalls = 0;
    const sourceItem = { identifier: 'mural-1', title: 'Community mural', description: 'Public artwork', type: 'artwork', creator: 'Amina', location: 'Dzaleka', source_date: 'Approximate, 2013', tags: ['art'], url: 'https://services.dzaleka.com/api/artworks#mural-1' };
    await page.route('**/api/sources/artworks*', async route => {
      sourceCalls++;
      const isDraft = route.request().url().includes('?id=');
      if (sourceCalls === 1) return route.fulfill({ status: 429, json: { error: 'Service busy.', retry_after: 1 } });
      if (isDraft) return route.fulfill({ json: { draft: { ...imported, id: 'df0202bc-788c-4551-8e6b-e3dc394ed545', title: sourceItem.title, type: 'artwork', language: '', rights: { access_level: 'restricted', consent_status: 'unknown' } } } });
      return route.fulfill({ json: { items: [sourceItem], cached: false } });
    });
    await page.getByRole('navigation').getByRole('button', { name: 'Sources', exact: true }).click();
    assert.equal(sourceCalls, 0);
    await page.getByRole('button', { name: 'Load collection', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'Retry in 1 seconds' }).waitFor();
    await page.getByRole('button', { name: 'Load collection', exact: true }).click();
    await page.getByRole('heading', { name: 'Community mural' }).waitFor();
    await page.getByLabel('Search loaded items', { exact: true }).fill('unmatched');
    await page.getByRole('heading', { name: 'No matching items' }).waitFor();
    await page.getByLabel('Search loaded items', { exact: true }).fill('');
    await page.getByRole('button', { name: 'Create draft', exact: true }).click();
    await page.waitForFunction(() => document.getElementById('title')?.value === 'Community mural');
    await page.getByRole('button', { name: 'Validate', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'Check these fields' }).waitFor();
    assert.equal(await page.getByLabel('Language code', { exact: true }).inputValue(), '');
    assert.equal((await (await page.request.get(url + '/api/records')).json()).length, 2);

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(__dirname, '../test-results/mobile-editor.png'), fullPage: true });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.getByRole('navigation').getByRole('button', { name: 'Overview', exact: true }).click();
    await page.screenshot({ path: path.join(__dirname, '../test-results/mobile.png'), fullPage: true });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(external, [], 'No browser-side external requests');
    assert.deepEqual(errors, [], 'No runtime or CSP errors');
    console.log('Browser checks passed: create, save, edit, all-field import, exports, vocabulary, source retry/import, draft protection, and mobile layout.');
  } catch (error) {
    if (page) {
      console.error(await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth, overflow: [...document.querySelectorAll('body *')].filter(node => node.getBoundingClientRect().right > innerWidth + 2).slice(0, 20).map(node => ({ tag: node.tagName, cls: node.className, right: node.getBoundingClientRect().right, position: getComputedStyle(node).position, overflow: getComputedStyle(node).overflow })) })));
      await page.screenshot({ path: path.join(__dirname, '../test-results/failure.png'), fullPage: true }).catch(() => {});
      console.error((await page.locator('body').innerText()).slice(-7000));
    }
    throw error;
  } finally {
    if (browser) await browser.close();
    const stopped = once(server, 'exit');
    server.kill('SIGINT');
    await stopped;
    lines.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
