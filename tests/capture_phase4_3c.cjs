const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

const port = process.env.CREW_PORT || process.argv[2] || '8765';
const token = process.env.CREW_API_TOKEN || process.argv[3] || '';
const screenshotDir = path.resolve(__dirname, 'screenshots');

fs.mkdirSync(screenshotDir, { recursive: true });

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1280,
    minHeight: 800,
    show: true,
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
    win.webContents.on('console-message', (event, level, message) => {
      console.log(`[Renderer Console] ${message}`);
    });

    const targetUrl = `http://127.0.0.1:${port}/`;
    console.log(`[Capture] Loading backend static URL: ${targetUrl}`);

    // Wait until loaded
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

    await new Promise(r => setTimeout(r, 3000));

    // Capture 1: Channel loaded
    const cap1 = await win.webContents.capturePage();
    fs.writeFileSync(path.join(screenshotDir, 'phase4_3c_1_channel_loaded.png'), cap1.toPNG());
    console.log('[Capture 1] Successfully captured phase4_3c_1_channel_loaded.png');

    // Submit teacher request
    const promptText = "본문 없이 일반 주제로 논술형 1문항과 4수준 루브릭 만들어줘";
    console.log(`[Capture] Submitting request: ${promptText}`);

    await new Promise(r => setTimeout(r, 1000));

    await win.webContents.executeJavaScript(`
      (() => {
        const textarea = document.querySelector('textarea');
        if (!textarea) return { error: 'No textarea' };

        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
        nativeSetter.call(textarea, ${JSON.stringify(promptText)});
        textarea.dispatchEvent(new Event('input', { bubbles: true }));

        setTimeout(() => {
          const buttons = Array.from(document.querySelectorAll('button'));
          const sendBtn = buttons.find(b => b.textContent.includes('보내기'));
          if (sendBtn) {
            sendBtn.click();
            console.log('[Capture Injected] Clicked send button');
          }
        }, 500);

        return { success: true };
      })()
    `);

    // Poll for approval card in DOM
    console.log('[Capture] Waiting for approval card...');
    let approvalFound = false;
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 2000));
      const hasCard = await win.webContents.executeJavaScript(`
        (() => {
          const buttons = Array.from(document.querySelectorAll('button'));
          return buttons.some(b => b.textContent.trim() === '승인');
        })()
      `);
      if (hasCard) {
        approvalFound = true;
        break;
      }
    }

    if (!approvalFound) {
      throw new Error('Approval card did not appear within 120s');
    }

    await new Promise(r => setTimeout(r, 1500));

    // Capture 2: Approval card
    const cap2 = await win.webContents.capturePage();
    fs.writeFileSync(path.join(screenshotDir, 'phase4_3c_2_approval_card.png'), cap2.toPNG());
    console.log('[Capture 2] Successfully captured phase4_3c_2_approval_card.png');

    // Click Approve button
    console.log('[Capture] Clicking approve button...');
    await win.webContents.executeJavaScript(`
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const approveBtn = buttons.find(b => b.textContent.trim() === '승인');
        if (approveBtn) approveBtn.click();
      })()
    `);

    // Wait for RightPanel deliverable to display and Word download button to appear
    await new Promise(r => setTimeout(r, 3500));

    // Capture 3: Approved and docx export available
    const cap3 = await win.webContents.capturePage();
    fs.writeFileSync(path.join(screenshotDir, 'phase4_3c_3_approved_docx.png'), cap3.toPNG());
    console.log('[Capture 3] Successfully captured phase4_3c_3_approved_docx.png');

    console.log('[Capture] All 3 screens captured successfully!');
  } catch (err) {
    console.error('[Capture Error]', err);
    process.exitCode = 1;
  } finally {
    app.quit();
  }
});
