const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { spawn, execSync } = require('child_process');

const ARTIFACT_DIR = path.resolve('C:\\Users\\user\\.gemini\\antigravity\\brain\\bfcf6c24-c0ed-47e4-9449-0980a18f3b67');

async function waitForPort(port, timeoutMs = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get(`http://127.0.0.1:${port}`, (res) => {
          resolve(true);
        });
        req.on('error', reject);
        req.setTimeout(1000, () => {
          req.destroy();
          reject(new Error('timeout'));
        });
      });
      return true;
    } catch (e) {
      await new Promise(r => setTimeout(r, 600));
    }
  }
  return false;
}

app.whenReady().then(async () => {
  console.log('[Hosting Test] Launching Firebase Hosting emulator...');
  
  // Launch firebase emulator via npx firebase-tools
  const emulatorProcess = spawn('npx.cmd', ['firebase-tools', 'emulators:start', '--only', 'hosting', '--project', 'demo-englishcrew'], {
    cwd: path.resolve(__dirname, '..'),
    shell: true,
    stdio: 'pipe'
  });

  emulatorProcess.stdout.on('data', (d) => {
    const s = d.toString();
    console.log(`[Firebase] ${s.trim()}`);
  });

  emulatorProcess.stderr.on('data', (d) => {
    const s = d.toString();
    console.error(`[Firebase ERR] ${s.trim()}`);
  });

  console.log('[Hosting Test] Waiting for Hosting emulator on http://127.0.0.1:5000 ...');
  const ready = await waitForPort(5000, 35000);
  if (!ready) {
    try { execSync(`taskkill /pid ${emulatorProcess.pid} /T /F`); } catch (e) {}
    throw new Error('Firebase hosting emulator failed to start on port 5000 within 35s');
  }

  console.log('[Hosting Test] Hosting emulator is UP! Opening Electron window to preview...');
  const win = new BrowserWindow({
    width: 1080,
    height: 980,
    show: true,
    webPreferences: {
      sandbox: true,
      contextIsolation: true
    }
  });

  await win.loadURL('http://127.0.0.1:5000');
  console.log('[Hosting Test] Page loaded successfully!');

  // Verify elements and download link formatting
  const links = await win.webContents.executeJavaScript(`
    ({
      setupHref: document.getElementById('download-setup') ? document.getElementById('download-setup').getAttribute('href') : null,
      portableHref: document.getElementById('download-portable') ? document.getElementById('download-portable').getAttribute('href') : null,
      title: document.title,
      h1: document.querySelector('h1') ? document.querySelector('h1').innerText : null
    })
  `);

  console.log('[Hosting Test] Page Info:', links);
  console.log(`  -> Setup URL    : ${links.setupHref}`);
  console.log(`  -> Portable URL : ${links.portableHref}`);

  const expectedSetup = 'https://github.com/googyosoo/english-crew-releases/releases/latest/download/EnglishCrew-Setup.exe';
  const expectedPortable = 'https://github.com/googyosoo/english-crew-releases/releases/latest/download/EnglishCrew-Portable.exe';

  if (links.setupHref !== expectedSetup) {
    throw new Error(`Expected setup href: ${expectedSetup}, got: ${links.setupHref}`);
  }
  if (links.portableHref !== expectedPortable) {
    throw new Error(`Expected portable href: ${expectedPortable}, got: ${links.portableHref}`);
  }

  await new Promise(r => setTimeout(r, 1000));

  // Capture screenshot
  const image = await win.capturePage();
  const screenshotPath = path.join(ARTIFACT_DIR, 'phase5_3_hosting_preview.png');
  fs.writeFileSync(screenshotPath, image.toPNG());
  console.log(`[Hosting Test] Saved hosting preview screenshot to: ${screenshotPath}`);

  win.close();

  // Terminate emulator cleanly
  console.log('[Hosting Test] Shutting down emulator...');
  try {
    execSync(`taskkill /pid ${emulatorProcess.pid} /T /F`);
  } catch (e) {}

  console.log('ALL PHASE 5-3 FIREBASE HOSTING PREVIEW AND LINK VERIFICATIONS PASSED 100%!');
  process.exit(0);
});
