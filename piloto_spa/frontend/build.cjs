const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const esbuild = require('esbuild');

const fuente = path.resolve(__dirname, '../backend/static/index.html');
const destino = path.resolve(__dirname, 'dist');
const html = fs.readFileSync(fuente, 'utf8');
const script = /<script type="text\/babel">([\s\S]+?)<\/script>/;
const jsx = html.match(script);
if (!jsx) throw new Error('No se encontró la entrada JSX.');

fs.mkdirSync(destino, { recursive: true });
esbuild.buildSync({
  stdin: {
    contents: "import React from 'react';\nimport * as ReactDOM from 'react-dom/client';\n" + jsx[1],
    loader: 'jsx',
    resolveDir: __dirname,
  },
  bundle: true,
  minify: true,
  outfile: path.join(destino, 'app.js'),
  define: { 'process.env.NODE_ENV': '"production"' },
});
execFileSync(process.execPath, [require.resolve('tailwindcss/lib/cli.js'), '--content', fuente,
  '--input', path.join(__dirname, 'styles.css'), '--output', path.join(destino, 'app.css'), '--minify'],
  { stdio: 'inherit' });
fs.writeFileSync(path.join(destino, 'index.html'), html
  .replace('</head>', '<link rel="stylesheet" href="/assets/app.css">\n</head>')
  .replace(script, '<script defer src="/assets/app.js"></script>'));
