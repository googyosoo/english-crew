import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

console.log('=== Phase 1 Scaffolding & UI Shell Automated Verification ===\n');

let passedTests = 0;
let totalTests = 0;

function assert(condition, testName, details = '') {
  totalTests++;
  if (condition) {
    console.log(`[PASS] ${testName}`);
    passedTests++;
  } else {
    console.error(`[FAIL] ${testName} - ${details}`);
    process.exitCode = 1;
  }
}

// 1. Electron Configuration & Security Check
const mainJsPath = path.join(rootDir, 'desktop', 'main.js');
assert(fs.existsSync(mainJsPath), 'desktop/main.js exists');
const mainJsContent = fs.readFileSync(mainJsPath, 'utf8');

assert(
  mainJsContent.includes('contextIsolation: true'),
  'Electron security: contextIsolation is true'
);
assert(
  mainJsContent.includes('nodeIntegration: false'),
  'Electron security: nodeIntegration is false'
);
assert(
  mainJsContent.includes('minWidth: 1280') && mainJsContent.includes('minHeight: 800'),
  'Window minimum size: 1280x800 enforced'
);
assert(
  fs.existsSync(path.join(rootDir, 'desktop', 'preload.js')),
  'desktop/preload.js exists'
);

// 2. Layout Structure & Widths Check
const sidebarPath = path.join(rootDir, 'frontend', 'src', 'components', 'Sidebar.jsx');
assert(fs.existsSync(sidebarPath), 'Sidebar.jsx exists');
const sidebarContent = fs.readFileSync(sidebarPath, 'utf8');
assert(
  sidebarContent.includes('w-[240px]'),
  'Sidebar width: exactly 240px'
);

const rightPanelPath = path.join(rootDir, 'frontend', 'src', 'components', 'RightPanel.jsx');
assert(fs.existsSync(rightPanelPath), 'RightPanel.jsx exists');
const rightPanelContent = fs.readFileSync(rightPanelPath, 'utf8');
assert(
  rightPanelContent.includes('w-[320px]'),
  'RightPanel width: exactly 320px'
);

// 3. Message Cards 4 Types Check
const messageCardTypes = ['TextMessage.jsx', 'DispatchCard.jsx', 'ApprovalCard.jsx', 'ReportCard.jsx'];
for (const cardFile of messageCardTypes) {
  const cardPath = path.join(rootDir, 'frontend', 'src', 'components', 'messages', cardFile);
  assert(fs.existsSync(cardPath), `Message card exists: ${cardFile}`);
}

// 4. Mock Data Specification Check
const mockDataPath = path.join(rootDir, 'frontend', 'src', 'mocks', 'mockData.js');
assert(fs.existsSync(mockDataPath), 'mockData.js exists');
const mockDataContent = fs.readFileSync(mockDataPath, 'utf8');

assert(
  mockDataContent.includes('전체 교무회의') &&
  mockDataContent.includes('영어I') &&
  mockDataContent.includes('심화영어I') &&
  mockDataContent.includes('심화영어독해I') &&
  mockDataContent.includes('진로영어'),
  'All 5 channels defined in mock data'
);

assert(
  mockDataContent.includes('코디봇') &&
  mockDataContent.includes('교육과정봇') &&
  mockDataContent.includes('수업봇') &&
  mockDataContent.includes('평가봇') &&
  mockDataContent.includes('기록봇'),
  'All 5 bots defined in mock data'
);

assert(
  mockDataContent.includes('논술형 1문항과 4수준 루브릭으로 확정하시겠습니까?'),
  'Scenario approval question matches PLAN.md 1-4'
);

// 5. Frontend Build Output Check
const distIndexPath = path.join(rootDir, 'frontend', 'dist', 'index.html');
assert(fs.existsSync(distIndexPath), 'frontend/dist/index.html generated');
const distHtml = fs.readFileSync(distIndexPath, 'utf8');
assert(distHtml.includes('English Crew'), 'Title in built index.html is English Crew');

// 6. Rules and Docs Check
assert(fs.existsSync(path.join(rootDir, 'docs', 'PLAN.md')), 'docs/PLAN.md exists');
assert(fs.existsSync(path.join(rootDir, '.gitignore')), '.gitignore exists');
const gitignoreContent = fs.readFileSync(path.join(rootDir, '.gitignore'), 'utf8');
assert(gitignoreContent.includes('data/') && gitignoreContent.includes('.env'), '.gitignore excludes data/ and .env');

console.log(`\nVerification Result: ${passedTests}/${totalTests} tests passed.`);
if (passedTests === totalTests) {
  console.log('All automated checks PASSED successfully!');
} else {
  process.exit(1);
}
