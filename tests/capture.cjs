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

    // 1. Capture initial 영어I channel with Phase 2 scenario
    console.log('[2/4] Capturing phase2_scenario_initial.png...');
    const imgInitial = await win.webContents.capturePage();
    const initialBuf = imgInitial.toPNG();
    fs.writeFileSync(path.join(screenshotDir, 'phase2_scenario_initial.png'), initialBuf);
    console.log('Saved phase2_scenario_initial.png (size:', initialBuf.length, 'bytes)');

    // 2. Click [승인] button on the approval card
    console.log('[3/4] Clicking 승인 button on ApprovalCard...');
    const clickRes = await win.webContents.executeJavaScript(`
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const approveBtn = buttons.find(b => b.innerText && b.innerText.includes('승인'));
        if (!approveBtn) return { error: '승인 버튼을 찾을 수 없습니다.', allButtons: buttons.map(b => b.innerText) };
        approveBtn.click();
        return { success: true, text: approveBtn.innerText };
      })()
    `);
    console.log('Approve click result:', clickRes);

    await new Promise(r => setTimeout(r, 2000));

    // 3. Capture approved state
    console.log('[4/4] Capturing phase2_scenario_approved.png...');
    const imgApproved = await win.webContents.capturePage();
    const approvedBuf = imgApproved.toPNG();
    fs.writeFileSync(path.join(screenshotDir, 'phase2_scenario_approved.png'), approvedBuf);
    console.log('Saved phase2_scenario_approved.png (size:', approvedBuf.length, 'bytes)');

    console.log('[SUCCESS] All Phase 2 scenario screenshots captured successfully!');
  } catch (err) {
    console.error(err);
    process.exitCode = 1;
  } finally {
    app.quit();
  }
});
