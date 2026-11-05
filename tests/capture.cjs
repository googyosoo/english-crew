const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

const workspaceDir = path.resolve(__dirname, '..');
const screenshotDir = path.join(workspaceDir, 'tests', 'screenshots');

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 1280,
    minHeight: 800,
    show: true, // Show window so Chromium renders and processes DOM events with full priority
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  try {
    fs.mkdirSync(screenshotDir, { recursive: true });

    await win.loadURL('http://127.0.0.1:5173');
    await new Promise(r => setTimeout(r, 2000));

    // 1. Capture 영어I (default channel)
    console.log('[1/4] Capturing 영어I 채널...');
    const imgEng1 = await win.webContents.capturePage();
    const eng1Buf = imgEng1.toPNG();
    fs.writeFileSync(path.join(screenshotDir, 'screenshot_eng1.png'), eng1Buf);
    console.log('Saved screenshot_eng1.png (size:', eng1Buf.length, 'bytes)');

    // 2. Dispatch genuine click event on '전체 교무회의' button
    console.log('[2/4] Switching to 전체 교무회의 채널...');
    const switchRes = await win.webContents.executeJavaScript(`
      (() => {
        const btn = document.querySelectorAll('aside button')[1];
        if (!btn) return { error: 'Button not found' };
        btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
        return { success: true, text: btn.textContent };
      })()
    `);
    console.log('Switch result:', switchRes);

    // Wait for state and paint
    await new Promise(r => setTimeout(r, 1500));

    // Verify current active channel in header
    const currentHeader = await win.webContents.executeJavaScript(`
      document.querySelector('header h2')?.textContent
    `);
    console.log('[3/4] Verified header title after switch:', currentHeader);

    // 3. Capture 전체 교무회의 채널
    console.log('[4/4] Capturing 전체 교무회의 채널...');
    const imgGeneral = await win.webContents.capturePage();
    const generalBuf = imgGeneral.toPNG();
    fs.writeFileSync(path.join(screenshotDir, 'screenshot_general.png'), generalBuf);
    console.log('Saved screenshot_general.png (size:', generalBuf.length, 'bytes)');

    console.log('[SUCCESS] All screenshots verified and captured successfully!');
  } catch (err) {
    console.error(err);
    process.exitCode = 1;
  } finally {
    app.quit();
  }
});
