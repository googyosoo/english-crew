const { contextBridge, ipcRenderer } = require('electron');

// Parse token and port passed via additionalArguments
const tokenArg = process.argv.find(arg => typeof arg === 'string' && arg.startsWith('--crew-token='));
const portArg = process.argv.find(arg => typeof arg === 'string' && arg.startsWith('--crew-port='));
const apiToken = tokenArg ? tokenArg.split('=')[1] : '';
const apiPort = portArg ? parseInt(portArg.split('=')[1], 10) : 8765;

// Verify that the current executing window is hosted at an authorized app origin
function isAllowedAppOrigin() {
  try {
    if (typeof window === 'undefined' || !window.location || !window.location.href) {
      return false;
    }
    const origin = window.location.origin;
    if (!origin || origin === 'null' || origin === 'about:blank') {
      return false;
    }
    const url = new URL(origin);
    const isLocalhost = url.hostname === '127.0.0.1' || url.hostname === 'localhost';
    const isAllowedPort = url.port === String(apiPort) || url.port === '5173';
    return url.protocol === 'http:' && isLocalhost && isAllowedPort;
  } catch (e) {
    return false;
  }
}

// Expose safe, isolated APIs to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  ping: () => 'pong',
  getToken: () => {
    if (!isAllowedAppOrigin()) {
      console.warn('[Security] Unauthorized origin attempted to retrieve API token:', typeof window !== 'undefined' ? window.location.origin : 'unknown');
      return '';
    }
    return apiToken;
  },
  getPort: () => apiPort,
  getApiUrl: () => `http://127.0.0.1:${apiPort}`,
  getApiConfig: async () => {
    if (!isAllowedAppOrigin()) {
      throw new Error('[Security] Unauthorized origin');
    }
    return await ipcRenderer.invoke('get-api-config');
  }
});
