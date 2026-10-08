const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const projectRoot = path.resolve(__dirname, '..');

test('首次进入使用空白快速体检而不是演示家庭结论', () => {
  const constants = fs.readFileSync(path.join(projectRoot, 'src/constants.js'), 'utf8');
  const app = fs.readFileSync(path.join(projectRoot, 'scripts/app_jsx.js'), 'utf8');

  assert.match(constants, /export const EMPTY_STATE =/);
  assert.match(constants, /assessmentCompleted:\s*false/);
  assert.match(app, /return EMPTY_STATE;/);
  assert.match(app, /useState\('quick'\)/);
  assert.match(app, /activeTab === 'quick'/);
  assert.match(app, /3分钟家庭快速体检/);
});

test('演示数据必须由用户显式加载且重置回空白状态', () => {
  const app = fs.readFileSync(path.join(projectRoot, 'scripts/app_jsx.js'), 'utf8');

  assert.match(app, /handleLoadDemo/);
  assert.match(app, /\.\.\.INITIAL_STATE/);
  assert.match(app, /assets: prev\.board\.assets/);
  assert.match(app, /查看示例演示/);
  assert.match(app, /\.\.\.EMPTY_STATE/);
  assert.doesNotMatch(app, /恢复系统演示初始配置/);
});

test('快速体检结论由家庭评估模型生成并显示资料完整度', () => {
  const app = fs.readFileSync(path.join(projectRoot, 'scripts/app_jsx.js'), 'utf8');

  assert.match(app, /runFamilyAssessment\(state\)/);
  assert.match(app, /资料完整度/);
  assert.match(app, /前三项行动/);
  assert.match(app, /建议配置区间/);
});
