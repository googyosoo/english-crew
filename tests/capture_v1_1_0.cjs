const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

const port = process.argv[2] || process.env.CREW_PORT || '8765';
const token = process.argv[3] || process.env.CREW_API_TOKEN || '';
const artifactDir = 'C:\\Users\\user\\.gemini\\antigravity\\brain\\bfcf6c24-c0ed-47e4-9449-0980a18f3b67';

fs.mkdirSync(artifactDir, { recursive: true });

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1280,
    minHeight: 800,
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.resolve(__dirname, '../desktop/preload.js'),
      additionalArguments: [
        `--crew-token=${token}`,
        `--crew-port=${port}`
      ]
    }
  });

  try {
    const targetUrl = `http://127.0.0.1:${port}/`;
    console.log(`[Capture] Loading backend URL: ${targetUrl}`);

    let loaded = false;
    for (let i = 0; i < 30; i++) {
      try {
        await win.loadURL(targetUrl);
        loaded = true;
        break;
      } catch (err) {
        await new Promise(r => setTimeout(r, 500));
      }
    }
    if (!loaded) throw new Error(`Could not load ${targetUrl}`);

    // Wait for channel rendering and messages to populate
    await new Promise(r => setTimeout(r, 4000));

    const image = await win.webContents.capturePage();
    const destPath = path.join(artifactDir, 'v1_1_0_live_screen.png');
    fs.writeFileSync(destPath, image.toPNG());
    console.log(`[Capture] Successfully captured ${destPath}`);

    // Also copy to tests/screenshots/
    const testScreenshotDir = path.resolve(__dirname, 'screenshots');
    fs.mkdirSync(testScreenshotDir, { recursive: true });
    fs.writeFileSync(path.join(testScreenshotDir, 'v1_1_0_live_screen.png'), image.toPNG());

  } catch (err) {
    console.error(`[Capture Error] ${err.message}`);
  } finally {
    win.destroy();
    app.quit();
  }
});
