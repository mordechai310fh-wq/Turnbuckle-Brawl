// Packages the game next to the untouched, officially built Electron runtime (Windows Smart App Control blocks
// electron-builder's modified exe on this PC), then zips it for sharing.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const root = path.join(__dirname, '..');
const out = path.join(root, 'dist', 'Turnbuckle Brawl');
require('./prepare.js');
fs.rmSync(out, { recursive: true, force: true });
fs.cpSync(path.join(root, 'node_modules', 'electron', 'dist'), out, { recursive: true });
fs.renameSync(path.join(out, 'electron.exe'), path.join(out, 'Turnbuckle Brawl.exe'));
fs.rmSync(path.join(out, 'resources', 'default_app.asar'), { force: true });
const appDir = path.join(out, 'resources', 'app');
fs.mkdirSync(appDir, { recursive: true });
fs.copyFileSync(path.join(root, 'main.js'), path.join(appDir, 'main.js'));
fs.copyFileSync(path.join(root, 'build', 'icon.ico'), path.join(appDir, 'icon.ico')); // window + shortcut icon (the exe itself must stay untouched)
fs.cpSync(path.join(root, 'app'), path.join(appDir, 'app'), { recursive: true });
const pkg = require(path.join(root, 'package.json'));
fs.writeFileSync(path.join(appDir, 'package.json'), JSON.stringify({ name: pkg.name, productName: pkg.productName, version: pkg.version, main: 'main.js' }, null, 1));
const zip = path.join(root, 'dist', `TurnbuckleBrawl-v${pkg.version}-Windows.zip`);
fs.rmSync(zip, { force: true });
execFileSync('python', ['-c', `import shutil; shutil.make_archive(r'${zip.replace(/\.zip$/, '')}', 'zip', r'${path.dirname(out)}', 'Turnbuckle Brawl')`], { stdio: 'inherit' });
console.log('packed:', out, '\nzip:', zip);
