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

    console.log('[1/5] Loading app from Vite dev server...');
    await win.loadURL('http://127.0.0.1:5173');
    await new Promise(r => setTimeout(r, 2000));

    // 1. Check sidebar health status
    const healthStatus = await win.webContents.executeJavaScript(`
      document.querySelector('aside > div:last-child span.font-medium')?.textContent
    `);
    console.log('Sidebar health text:', healthStatus);

    // 2. Type message into input area and submit
    const promptText = "영어I 3과 본문으로 논술형 1문항과 4수준 루브릭 만들어줘";
    console.log('[2/5] Submitting prompt:', promptText);
    const submitRes = await win.webContents.executeJavaScript(`
      (() => {
        const textarea = document.querySelector('textarea');
        if (!textarea) return { error: 'Textarea not found' };

        // Set value and trigger input event
        textarea.value = ${JSON.stringify(promptText)};
        textarea.dispatchEvent(new Event('input', { bubbles: true }));

        const buttons = Array.from(document.querySelectorAll('button'));
        const sendBtn = buttons.find(b => b.textContent.includes('보내기'));
        if (!sendBtn) return { error: 'Send button not found' };

        sendBtn.click();
        return { success: true };
      })()
    `);
    console.log('Submit result:', submitRes);

    // 3. Wait for Gemini processing (Coordinator dispatch -> Assessment task -> Approval card)
    console.log('[3/5] Waiting for Gemini crew generation (up to 90s)...');
    let approvalFound = false;
    for (let i = 0; i < 45; i++) {
      await new Promise(r => setTimeout(r, 2000));
      const state = await win.webContents.executeJavaScript(`
        (() => {
          const buttons = Array.from(document.querySelectorAll('button'));
          const approveBtn = buttons.find(b => b.textContent.trim() === '승인');
          const errorMsg = document.querySelector('div.bg-rose-50, div.text-rose-700')?.textContent;
          return {
            hasApproveBtn: !!approveBtn,
            error: errorMsg || null,
            messageCount: document.querySelectorAll('main > div > div').length
          };
        })()
      `);

      if (state.error) {
        console.error('Error detected during generation:', state.error);
        break;
      }

      if (state.hasApproveBtn) {
        console.log('ApprovalCard detected with 승인 button!');
        approvalFound = true;
        break;
      }

      if (i % 5 === 0) {
        console.log(`Still processing... (${i * 2}s elapsed)`);
      }
    }

    // Wait 1.5s for paint
    await new Promise(r => setTimeout(r, 1500));

    // 4. Capture phase2_real_initial.png
    console.log('[4/5] Capturing phase2_real_initial.png...');
    const imgInitial = await win.webContents.capturePage();
    const initialBuf = imgInitial.toPNG();
    fs.writeFileSync(path.join(screenshotDir, 'phase2_real_initial.png'), initialBuf);
    console.log('Saved phase2_real_initial.png (size:', initialBuf.length, 'bytes)');

    if (approvalFound) {
      // 5. Click [승인] button
      console.log('[5/5] Clicking 승인 button...');
      await win.webContents.executeJavaScript(`
        (() => {
          const buttons = Array.from(document.querySelectorAll('button'));
          const approveBtn = buttons.find(b => b.textContent.trim() === '승인');
          if (approveBtn) approveBtn.click();
        })()
      `);

      await new Promise(r => setTimeout(r, 2000));

      const imgApproved = await win.webContents.capturePage();
      const approvedBuf = imgApproved.toPNG();
      fs.writeFileSync(path.join(screenshotDir, 'phase2_real_approved.png'), approvedBuf);
      console.log('Saved phase2_real_approved.png (size:', approvedBuf.length, 'bytes)');
    } else {
      console.warn('Approval card not found or failed, skipping approve click.');
    }

    console.log('[COMPLETED] E2E capture run finished.');
  } catch (err) {
    console.error('E2E capture error:', err);
    process.exitCode = 1;
  } finally {
    app.quit();
  }
});
