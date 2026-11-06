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
    show: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  try {
    fs.mkdirSync(screenshotDir, { recursive: true });

    console.log('[1/4] Loading app from Vite dev server...');
    await win.loadURL('http://127.0.0.1:5173');
    await new Promise(r => setTimeout(r, 2500));

    // 1. Capture real approved state in eng1 channel
    console.log('[2/4] Capturing phase2_real_approved.png...');
    const imgApproved = await win.webContents.capturePage();
    const approvedBuf = imgApproved.toPNG();
    fs.writeFileSync(path.join(screenshotDir, 'phase2_real_approved.png'), approvedBuf);
    console.log('Saved phase2_real_approved.png (size:', approvedBuf.length, 'bytes)');

    // 2. Click the first task item in ReportCard or DispatchCard to view deliverable in RightPanel
    console.log('[3/4] Clicking deliverable task item to render markdown in RightPanel...');
    const clickTaskRes = await win.webContents.executeJavaScript(`
      (() => {
        // Find clickable task row
        const taskRows = Array.from(document.querySelectorAll('div.cursor-pointer'));
        if (taskRows.length > 0) {
          taskRows[0].click();
          return { success: true, text: taskRows[0].textContent };
        }
        return { error: 'No clickable task row found' };
      })()
    `);
    console.log('Task click result:', clickTaskRes);

    await new Promise(r => setTimeout(r, 2000));

    // 3. Capture phase2_real_initial.png showing deliverable preview
    console.log('[4/4] Capturing phase2_real_initial.png (with Deliverable Preview)...');
    const imgInitial = await win.webContents.capturePage();
    const initialBuf = imgInitial.toPNG();
    fs.writeFileSync(path.join(screenshotDir, 'phase2_real_initial.png'), initialBuf);
    console.log('Saved phase2_real_initial.png (size:', initialBuf.length, 'bytes)');

    console.log('[SUCCESS] All real Phase 2 screenshots captured successfully!');
  } catch (err) {
    console.error('Error during capture:', err);
    process.exitCode = 1;
  } finally {
    app.quit();
  }
});
