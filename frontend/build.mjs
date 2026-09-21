import { build } from 'esbuild';
import { readFile, readdir, writeFile } from 'node:fs/promises';

const result = await build({
  entryPoints: ['src/main.jsx'],
  bundle: true,
  minify: true,
  format: 'esm',
  outfile: '../dms/static/app.js',
  loader: { '.woff': 'file', '.woff2': 'file' },
  define: { 'process.env.NODE_ENV': '"production"' },
  jsx: 'automatic',
  legalComments: 'linked',
  metafile: true,
  banner: { js: '/*! Third-party licenses: licenses.txt */', css: '/*! Third-party licenses: licenses.txt */' },
});

const packages = [...new Set(Object.keys(result.metafile.inputs)
  .map(file => file.match(/^node_modules\/((?:@[^/]+\/)?[^/]+)/)?.[1]).filter(Boolean))].sort();
const notices = ['Third-party software included in the DMS web app.'];
for (const name of packages) {
  const directory = `node_modules/${name}`;
  const metadata = JSON.parse(await readFile(`${directory}/package.json`, 'utf8'));
  const files = (await readdir(directory)).filter(file => /^(license|licence|copying)(\.|$)/i.test(file)).sort();
  if (!files.length) throw new Error(`Missing license text for bundled package ${name}`);
  notices.push(`${name} ${metadata.version}`, ...(await Promise.all(files.map(file => readFile(`${directory}/${file}`, 'utf8')))));
}
notices.push('Tailwind CSS (included in the Kumo standalone stylesheet)', await readFile('LICENSE.tailwind', 'utf8'));
await writeFile('../dms/static/licenses.txt', notices.map(notice => notice.trimEnd()).join('\n\n') + '\n');
