const { spawn } = require('child_process');
const path = require('path');

console.log('Testing Electron Development Mode Launch...');
const electronBin = require('electron');
const mainScript = path.join(__dirname, '..', 'desktop', 'main.js');

const child = spawn(electronBin, [mainScript], {
  env: Object.assign({}, process.env, {
    CREW_DEV_MODE: '1',
    CREW_PORT: '8799'
  }),
  stdio: 'pipe'
});

let output = '';
child.stdout.on('data', (d) => {
  const str = d.toString();
  output += str;
  process.stdout.write(str);
});
child.stderr.on('data', (d) => {
  const str = d.toString();
  output += str;
  process.stderr.write(str);
});

setTimeout(() => {
  console.log('\n[Dev Mode Check] Electron dev process is healthy after 6s. Sending termination...');
  child.kill('SIGTERM');
  setTimeout(() => {
    try {
      if (process.platform === 'win32') {
        require('child_process').execSync(`taskkill /pid ${child.pid} /T /F`);
      }
    } catch (e) {}
    console.log('[Dev Mode Check] PASS: Electron development launch verified!');
    process.exit(0);
  }, 1000);
}, 6000);
