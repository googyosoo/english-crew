const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const net = require('net');
const crypto = require('crypto');
const { spawn, execSync } = require('child_process');

let mainWindow = null;
let backendProcess = null;

// Generate 32-byte secure random token on each application launch
const apiToken = crypto.randomBytes(32).toString('hex');
let apiPort = 8765;

// Check if a specific port is free to listen on
function checkPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => {
      resolve(false);
    });
    server.once('listening', () => {
      server.close(() => resolve(true));
    });
    server.listen(port, '127.0.0.1');
  });
}

// Find an available dynamic port by listening on port 0
function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
    server.on('error', reject);
  });
}

async function determineBackendPort() {
  const isDefaultFree = await checkPortAvailable(8765);
  if (isDefaultFree) {
    return 8765;
  }
  const dynamicPort = await getFreePort();
  console.log(`[Backend] Port 8765 is currently in use. Selected dynamic port: ${dynamicPort}`);
  return dynamicPort;
}

async function startBackend() {
  const rootDir = path.join(__dirname, '..');
  const isWin = process.platform === 'win32';
  const userDataPath = app.getPath('userData');
  const dataDir = path.join(userDataPath, 'data');

  try {
    fs.mkdirSync(dataDir, { recursive: true });
  } catch (e) {
    console.warn('[Backend] Could not create userData data directory:', e);
  }

  apiPort = await determineBackendPort();
  console.log(`[Backend] Launching backend on port ${apiPort} with 32-byte security token`);

  const isPackaged = app.isPackaged;
  const packagedExe = path.join(process.resourcesPath, 'backend-dist', 'english-crew-backend.exe');

  if (isPackaged && fs.existsSync(packagedExe)) {
    console.log(`[Backend] Starting Packaged Binary: ${packagedExe}`);
    const env = Object.assign({}, process.env, {
      CREW_USER_DATA_DIR: userDataPath,
      CREW_DATA_DIR: dataDir,
      CREW_API_TOKEN: apiToken,
      CREW_PORT: String(apiPort),
      CREW_DEV_MODE: '0',
    });

    const args = ['--port', String(apiPort)];

    backendProcess = spawn(packagedExe, args, {
      cwd: userDataPath,
      env: env,
      shell: false,
      stdio: 'pipe',
    });
  } else {
    // Development mode
    const venvPythonWin = path.join(rootDir, 'backend', '.venv', 'Scripts', 'python.exe');
    const venvPythonPosix = path.join(rootDir, 'backend', '.venv', 'bin', 'python');

    let pythonPath = 'python';
    if (isWin && fs.existsSync(venvPythonWin)) {
      pythonPath = venvPythonWin;
    } else if (!isWin && fs.existsSync(venvPythonPosix)) {
      pythonPath = venvPythonPosix;
    }

    const env = Object.assign({}, process.env, {
      CREW_API_TOKEN: apiToken,
      CREW_PORT: String(apiPort),
      CREW_DEV_MODE: '1',
    });

    const args = ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', String(apiPort), '--no-access-log'];

    console.log(`[Backend] Starting FastAPI in dev mode on port ${apiPort} using: ${pythonPath}`);
    backendProcess = spawn(pythonPath, args, {
      cwd: rootDir,
      env: env,
      shell: false,
      stdio: 'pipe',
    });
  }

  backendProcess.stdout.on('data', (data) => {
    console.log(`[FastAPI] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[FastAPI] ${data.toString().trim()}`);
  });

  backendProcess.on('exit', (code, signal) => {
    console.log(`[FastAPI] Process exited with code ${code}, signal ${signal}`);
    backendProcess = null;
  });
}

function stopBackend() {
  if (backendProcess && backendProcess.pid) {
    console.log(`[Backend] Stopping FastAPI (PID: ${backendProcess.pid})`);
    try {
      if (process.platform === 'win32') {
        execSync(`taskkill /pid ${backendProcess.pid} /T /F`);
      } else {
        backendProcess.kill('SIGTERM');
      }
    } catch (e) {
      // Process may already be dead
    }
    backendProcess = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 1280,
    minHeight: 800,
    title: 'English Crew',
    backgroundColor: '#f8f9fa',
    webPreferences: {
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js'),
      additionalArguments: [
        `--crew-token=${apiToken}`,
        `--crew-port=${apiPort}`
      ]
    }
  });

  // Security P1: prevent in-app navigation away from app origin; open https links in external browser
  mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
    try {
      const parsed = new URL(navigationUrl);
      const isAllowedAppOrigin =
        (parsed.protocol === 'http:' && (parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost')) &&
        (parsed.port === String(apiPort) || parsed.port === '5173');

      if (!isAllowedAppOrigin) {
        event.preventDefault();
        console.log(`[Security] Blocked in-app navigation to: ${navigationUrl}`);
        if (parsed.protocol === 'https:') {
          shell.openExternal(navigationUrl);
        }
      }
    } catch (e) {
      event.preventDefault();
    }
  });

  // Security P1: deny all new window creation; open https links in external browser
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

  const devUrl = 'http://127.0.0.1:5173';
  const isDev = !app.isPackaged && process.env.NODE_ENV !== 'production';

  if (isDev) {
    const loadDevServer = () => {
      mainWindow.loadURL(devUrl).catch(() => {
        setTimeout(loadDevServer, 500);
      });
    };
    loadDevServer();
  } else {
    // Packaged mode: load from backend server serving static files (same-origin, no CORS needed)
    const backendUrl = `http://127.0.0.1:${apiPort}/`;
    const loadBackendServer = () => {
      mainWindow.loadURL(backendUrl).catch(() => {
        setTimeout(loadBackendServer, 300);
      });
    };
    loadBackendServer();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC handler to provide API config safely to renderer (restricted to allowed app origins)
ipcMain.handle('get-api-config', (event) => {
  const senderUrl = event.senderFrame ? event.senderFrame.url : (event.sender ? event.sender.getURL() : '');
  try {
    const parsed = new URL(senderUrl);
    const isAllowed =
      (parsed.protocol === 'http:' && (parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost')) &&
      (parsed.port === String(apiPort) || parsed.port === '5173');
    if (!isAllowed) {
      throw new Error(`Forbidden origin: ${senderUrl}`);
    }
  } catch (e) {
    throw new Error('Unauthorized origin');
  }

  return {
    token: apiToken,
    port: apiPort,
    apiUrl: `http://127.0.0.1:${apiPort}`
  };
});

app.whenReady().then(async () => {
  await startBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  stopBackend();
});

process.on('SIGINT', () => {
  stopBackend();
  process.exit(0);
});

process.on('SIGTERM', () => {
  stopBackend();
  process.exit(0);
});
