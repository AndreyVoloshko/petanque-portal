import { mkdir, readFile, writeFile } from 'node:fs/promises';

// Use only the CSS components needed by server-rendered lists. Prefix their
// classes so short names such as .btn, .badge and .table never hit Bootstrap.
const components = ['button', 'badge', 'table', 'input', 'native-select', 'empty'];
const classes = /\.(btn|badge|table-container|table|field|input|select|empty)\b/g;
const source = await Promise.all(components.map(async (name) => {
  const path = import.meta.resolve(`basecoat-css/components/${name}.css`);
  return (await readFile(new URL(path), 'utf8')).replace(classes, '.portal-$1');
}));
await mkdir('.generated', { recursive: true });
await writeFile('.generated/basecoat.css', source.join('\n'));
