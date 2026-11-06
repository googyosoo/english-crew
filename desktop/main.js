const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, execSync } = require('child_process');

let mainWindow = null;
let backendProcess = null;

function startBackend() {
  const rootDir = path.join(__dirname, '..');
  const isWin = process.platform === 'win32';
  const venvPythonWin = path.join(rootDir, 'backend', '.venv', 'Scripts', 'python.exe');
  const venvPythonPosix = path.join(rootDir, 'backend', '.venv', 'bin', 'python');
  
  let pythonPath = 'python';
  if (isWin && fs.existsSync(venvPythonWin)) {
    pythonPath = venvPythonWin;
  } else if (!isWin && fs.existsSync(venvPythonPosix)) {
    pythonPath = venvPythonPosix;
  }

  const args = ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8765'];

  console.log(`[Backend] Starting FastAPI using: ${pythonPath}`);
  backendProcess = spawn(pythonPath, args, {
    cwd: rootDir,
    shell: false,
    stdio: 'pipe',
  });

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
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  const devUrl = 'http://127.0.0.1:5173';
  const isDev = !app.isPackaged && process.env.NODE_ENV !== 'production';

  if (isDev) {
    // Retry loading in case Vite is still warming up
    const loadDevServer = () => {
      mainWindow.loadURL(devUrl).catch(() => {
        setTimeout(loadDevServer, 500);
      });
    };
    loadDevServer();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  startBackend();
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
