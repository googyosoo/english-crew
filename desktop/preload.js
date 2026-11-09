const { contextBridge, ipcRenderer } = require('electron');

// Parse token and port passed via additionalArguments
const tokenArg = process.argv.find(arg => typeof arg === 'string' && arg.startsWith('--crew-token='));
const portArg = process.argv.find(arg => typeof arg === 'string' && arg.startsWith('--crew-port='));
const apiToken = tokenArg ? tokenArg.split('=')[1] : '';
const apiPort = portArg ? parseInt(portArg.split('=')[1], 10) : 8765;

// Expose safe, isolated APIs to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  ping: () => 'pong',
  getToken: () => apiToken,
  getPort: () => apiPort,
  getApiUrl: () => `http://127.0.0.1:${apiPort}`,
  getApiConfig: () => ipcRenderer.invoke('get-api-config')
});
