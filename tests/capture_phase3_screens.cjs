const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

const workspaceDir = path.resolve(__dirname, '..');
const screenshotDir = path.join(workspaceDir, 'tests', 'screenshots');
const mode = process.argv[2] || 'initial'; // 'initial' or 'approved'

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 1280,
    minHeight: 800,
    show: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  try {
    fs.mkdirSync(screenshotDir, { recursive: true });

    console.log(`[Electron] Loading app for ${mode} capture...`);
    await win.loadURL('http://127.0.0.1:5173');
    await new Promise(r => setTimeout(r, 2500));

    // Click the task item to load deliverable in RightPanel
    await win.webContents.executeJavaScript(`
      (() => {
        const taskRows = Array.from(document.querySelectorAll('div.cursor-pointer'));
        if (taskRows.length > 0) {
          // click last or first task
          taskRows[taskRows.length - 1].click();
        }
      })()
    `);

    await new Promise(r => setTimeout(r, 1500));

    const filename = mode === 'approved' ? 'phase3_real_approved.png' : 'phase3_real_initial.png';
    const img = await win.webContents.capturePage();
    const buf = img.toPNG();
    fs.writeFileSync(path.join(screenshotDir, filename), buf);
    console.log(`[Electron] Successfully saved ${filename} (size: ${buf.length} bytes)`);

  } catch (err) {
    console.error('Error during capture:', err);
    process.exitCode = 1;
  } finally {
    app.quit();
  }
});
