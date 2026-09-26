const { app, BrowserWindow, session } = require('electron');
const path = require('path');

// keep the game loop running when the window is covered or minimized (an online host must keep simulating)
app.commandLine.appendSwitch('disable-features', 'CalculateNativeWinOcclusion');
app.commandLine.appendSwitch('disable-renderer-backgrounding');
app.commandLine.appendSwitch('disable-background-timer-throttling');

// `--profile=name` gives a separate save folder, so two copies can run side by side for testing
const profile = (process.argv.find(a => a.startsWith('--profile=')) || '').slice(10);
if (profile) app.setPath('userData', path.join(app.getPath('appData'), 'Turnbuckle Brawl', 'profiles', profile.replace(/[^\w-]/g, '')));

function createWindow() {
  // TB_OFFSCREEN=1 opens the window off-screen (used for automated testing)
  const off = process.env.TB_OFFSCREEN === '1';
  const win = new BrowserWindow({
    width: 1440, height: 860, minWidth: 800, minHeight: 540,
    ...(off ? { x: -4000, y: 0, skipTaskbar: true, focusable: false } : {}),
    backgroundColor: '#09080f', title: 'Turnbuckle Brawl', autoHideMenuBar: true, icon: path.join(__dirname, 'icon.ico'),
    webPreferences: { contextIsolation: true, backgroundThrottling: false },
  });
  win.removeMenu();
  win.loadFile(path.join(__dirname, 'app', 'index.html'));
  // F11 toggles fullscreen
  win.webContents.on('before-input-event', (e, input) => {
    if (input.type === 'keyDown' && input.key === 'F11') { win.setFullScreen(!win.isFullScreen()); e.preventDefault(); }
  });
}

// TB_FAKEMIC=1 feeds a test tone instead of a real microphone (automated voice-chat testing)
if (process.env.TB_FAKEMIC === '1') {
  app.commandLine.appendSwitch('use-fake-device-for-media-stream');
  app.commandLine.appendSwitch('use-fake-ui-for-media-stream');
}

app.whenReady().then(() => {
  // voice chat needs the microphone; allow it for the game's own page only
  const ok = (wc, perm) => (perm === 'media' || perm === 'microphone' || perm === 'audioCapture') && wc.getURL().startsWith('file://');
  session.defaultSession.setPermissionRequestHandler((wc, perm, cb) => cb(ok(wc, perm)));
  session.defaultSession.setPermissionCheckHandler((wc, perm) => !!wc && ok(wc, perm));
  createWindow();
});
app.on('window-all-closed', () => app.quit());
