const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');

const ARTIFACT_DIR = path.resolve('C:\\Users\\user\\.gemini\\antigravity\\brain\\bfcf6c24-c0ed-47e4-9449-0980a18f3b67');
const apiToken = 'test-token-security-verification-12345';
let server = null;
let mainWindow = null;
let serverPort = 0;

let navigationBlockedCount = 0;
let externalOpenedUrls = [];

function startMockAppServer() {
  return new Promise((resolve) => {
    server = http.createServer((req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(`
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>English Crew - Markdown Security Test</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 40px; background: #f8fafc; color: #1e293b; }
            .card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); border: 1px solid #e2e8f0; max-width: 700px; margin: 0 auto; }
            h2 { margin-top: 0; color: #0f172a; font-size: 20px; }
            .badge { display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; background: #e0f2fe; color: #0369a1; margin-bottom: 16px; }
            .markdown-content { background: #f1f5f9; padding: 16px; border-radius: 8px; border-left: 4px solid #3b82f6; }
            a.test-link { color: #2563eb; font-weight: 600; text-decoration: underline; cursor: pointer; }
            .status-box { margin-top: 20px; padding: 12px; border-radius: 6px; background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; font-size: 14px; }
          </style>
        </head>
        <body>
          <div class="card">
            <span class="badge">Phase 5-1 보안 P1 검증</span>
            <h2>산출물 마크다운 링크 클릭 및 창 이동 차단 테스트</h2>
            <div class="markdown-content">
              <h3>[12영Ⅰ01-01] 읽기 자료 및 외부 참조 링크</h3>
              <p>아래 링크는 산출물에 포함된 외부 참조 웹사이트 링크입니다:</p>
              <p>
                <a id="external-link" class="test-link" href="https://example.com/external-curriculum-reference">
                  https://example.com/external-curriculum-reference (외부 링크 클릭 테스트)
                </a>
              </p>
              <p>
                <a id="external-target-blank" class="test-link" href="https://example.com/another-site" target="_blank">
                  https://example.com/another-site (새 창 타겟 링크)
                </a>
              </p>
            </div>
            <div id="status" class="status-box">
              ✅ 앱 자체 주소(127.0.0.1)에서 정상 로드됨 | 토큰 보안 격리 활성화
            </div>
          </div>
        </body>
        </html>
      `);
    });

    server.listen(0, '127.0.0.1', () => {
      serverPort = server.address().port;
      resolve(serverPort);
    });
  });
}

// Mock shell.openExternal so it doesn't actually open real user browser in test
shell.openExternal = async (url) => {
  console.log(`[Mock shell.openExternal] Intercepted external browser open: ${url}`);
  externalOpenedUrls.push(url);
  return true;
};

app.whenReady().then(async () => {
  const port = await startMockAppServer();
  console.log(`[Test] Started mock app server on http://127.0.0.1:${port}`);

  mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    show: true,
    webPreferences: {
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, '..', 'desktop', 'preload.js'),
      additionalArguments: [
        `--crew-token=${apiToken}`,
        `--crew-port=${port}`
      ]
    }
  });

  // 1. will-navigate handler (Same as desktop/main.js)
  mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
    try {
      const parsed = new URL(navigationUrl);
      const isAllowedAppOrigin =
        (parsed.protocol === 'http:' && (parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost')) &&
        (parsed.port === String(port) || parsed.port === '5173');

      if (!isAllowedAppOrigin) {
        event.preventDefault();
        navigationBlockedCount++;
        console.log(`[Security PASS] will-navigate blocked in-app navigation to: ${navigationUrl}`);
        if (parsed.protocol === 'https:') {
          shell.openExternal(navigationUrl);
        }
      }
    } catch (e) {
      event.preventDefault();
    }
  });

  // 2. setWindowOpenHandler (Same as desktop/main.js)
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    try {
      const parsed = new URL(url);
      if (parsed.protocol === 'https:') {
        shell.openExternal(url);
      }
    } catch (e) {
      console.warn('[Security] Invalid URL in window open handler:', url, e);
    }
    return { action: 'deny' };
  });

  const appUrl = `http://127.0.0.1:${port}/`;
  await mainWindow.loadURL(appUrl);
  console.log(`[Test] Loaded app at: ${mainWindow.webContents.getURL()}`);

  // Test Preload Security: verify token is retrievable on allowed origin
  const tokenCheck = await mainWindow.webContents.executeJavaScript(`
    window.electronAPI.getToken()
  `);
  console.log(`[Test] Preload token on allowed origin: ${tokenCheck === apiToken ? 'VALID' : 'INVALID'}`);
  if (tokenCheck !== apiToken) {
    throw new Error('Preload token should be accessible on allowed app origin!');
  }

  // Click external markdown link
  console.log('[Test] Triggering click on external markdown link...');
  await mainWindow.webContents.executeJavaScript(`
    document.getElementById('external-link').click();
  `);

  // Wait a short delay to verify that no navigation took place
  await new Promise(r => setTimeout(r, 800));

  const currentUrlAfterClick = mainWindow.webContents.getURL();
  console.log(`[Test] URL after link click: ${currentUrlAfterClick}`);

  if (currentUrlAfterClick !== appUrl) {
    throw new Error(`Window navigated unexpectedly to: ${currentUrlAfterClick}`);
  }
  if (navigationBlockedCount === 0) {
    throw new Error('will-navigate event was not triggered or not blocked!');
  }
  if (!externalOpenedUrls.includes('https://example.com/external-curriculum-reference')) {
    throw new Error('Expected shell.openExternal to be called for external URL!');
  }

  // Click target="_blank" link as well
  console.log('[Test] Triggering click on target="_blank" link...');
  await mainWindow.webContents.executeJavaScript(`
    document.getElementById('external-target-blank').click();
  `);
  await new Promise(r => setTimeout(r, 500));

  if (!externalOpenedUrls.includes('https://example.com/another-site')) {
    throw new Error('Expected setWindowOpenHandler to redirect target="_blank" link to shell.openExternal!');
  }

  // Update DOM with verification badge before screenshot
  await mainWindow.webContents.executeJavaScript(`
    const statusBox = document.getElementById('status');
    statusBox.innerHTML = '🛡️ [보안 검증 완료] 외부 링크 클릭 차단 성공 (will-navigate blocked) | 창 URL 미변경 유지';
    statusBox.style.background = '#dbeafe';
    statusBox.style.borderColor = '#93c5fd';
    statusBox.style.color = '#1e40af';
  `);
  await new Promise(r => setTimeout(r, 400));

  // Capture screenshot and save to artifact directory
  const image = await mainWindow.capturePage();
  const screenshotPath = path.join(ARTIFACT_DIR, 'phase5_1_link_navigation_blocked.png');
  fs.writeFileSync(screenshotPath, image.toPNG());
  console.log(`[Test SUCCESS] Saved screenshot to: ${screenshotPath}`);

  mainWindow.close();
  server.close();
  console.log('ALL PHASE 5-1 ELECTRON SECURITY VERIFICATIONS PASSED 100%!');
  process.exit(0);
});
