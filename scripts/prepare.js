// Builds app/index.html from src/game.html: swaps CDN scripts for bundled copies and adds PeerJS for online play.
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const nm = p => path.join(root, 'node_modules', p);
const vendor = path.join(root, 'app', 'vendor');
fs.mkdirSync(vendor, { recursive: true });

const copies = {
  'three.min.js': 'three/build/three.min.js',
  'CopyShader.js': 'three/examples/js/shaders/CopyShader.js',
  'LuminosityHighPassShader.js': 'three/examples/js/shaders/LuminosityHighPassShader.js',
  'GammaCorrectionShader.js': 'three/examples/js/shaders/GammaCorrectionShader.js',
  'EffectComposer.js': 'three/examples/js/postprocessing/EffectComposer.js',
  'RenderPass.js': 'three/examples/js/postprocessing/RenderPass.js',
  'ShaderPass.js': 'three/examples/js/postprocessing/ShaderPass.js',
  'UnrealBloomPass.js': 'three/examples/js/postprocessing/UnrealBloomPass.js',
  'peerjs.min.js': 'peerjs/dist/peerjs.min.js',
  'GLTFLoader.js': 'three/examples/js/loaders/GLTFLoader.js',
  'SkeletonUtils.js': 'three/examples/js/utils/SkeletonUtils.js',
};
for (const [out, src] of Object.entries(copies)) fs.copyFileSync(nm(src), path.join(vendor, out));

let html = fs.readFileSync(path.join(root, 'src', 'game.html'), 'utf8');
html = html.replace(/<script src="https:\/\/[^"]+\/([A-Za-z]+(?:\.min)?\.js)"><\/script>/g, (m, file) => {
  if (!copies[file]) throw new Error('No bundled copy for ' + m);
  return `<script src="vendor/${file}"></script>`;
});
html = html.replace('<script src="vendor/three.min.js"></script>', '<script src="vendor/peerjs.min.js"></script>\n<script src="vendor/three.min.js"></script>');
// 3D character models: copy the converted .glb files and write the roster the game reads
const roster = JSON.parse(fs.readFileSync(path.join(root, 'tools', 'roster.json'), 'utf8'));
const modelsOut = path.join(root, 'app', 'models');
fs.rmSync(modelsOut, { recursive: true, force: true }); // drop fighters no longer in the roster
fs.mkdirSync(modelsOut, { recursive: true });
const present = roster.filter(d => fs.existsSync(path.join(root, 'models', d.file)));
for (const d of present) { fs.copyFileSync(path.join(root, 'models', d.file), path.join(modelsOut, d.file)); d.file = 'models/' + d.file; }
fs.writeFileSync(path.join(root, 'app', 'models.js'), 'window.TB_MODELS = ' + JSON.stringify(present, null, 1) + ';\n');
fs.appendFileSync(path.join(root, 'app', 'models.js'), 'window.TB_VERSION = ' + JSON.stringify(require(path.join(root, 'package.json')).version) + ';\n');
// the user's arena, if converted
const arenaCfg = path.join(root, 'tools', 'arena.json');
if (fs.existsSync(arenaCfg)) {
  const arena = JSON.parse(fs.readFileSync(arenaCfg, 'utf8'));
  if (fs.existsSync(path.join(root, 'models', arena.file))) {
    fs.copyFileSync(path.join(root, 'models', arena.file), path.join(modelsOut, arena.file));
    arena.file = 'models/' + arena.file;
    fs.appendFileSync(path.join(root, 'app', 'models.js'), 'window.TB_ARENA = ' + JSON.stringify(arena) + ';\n');
    console.log('arena:', arena.file);
  }
}
html = html.replace('<script src="vendor/UnrealBloomPass.js"></script>',
  '<script src="vendor/UnrealBloomPass.js"></script>\n<script src="vendor/GLTFLoader.js"></script>\n<script src="vendor/SkeletonUtils.js"></script>\n<script src="models.js"></script>');
console.log('models:', present.map(d => d.id).join(', '));

const head = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
  + '<style>html,body{margin:0}[hidden]{display:none!important}</style>\n';
html = head + html.replace('</style>', '</style>\n</head>\n<body>') + '\n</body>\n</html>\n';
fs.writeFileSync(path.join(root, 'app', 'index.html'), html);
console.log('app/index.html ready');
