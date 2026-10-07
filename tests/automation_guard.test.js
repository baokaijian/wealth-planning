const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const projectRoot = path.resolve(__dirname, '..');

test('行情工作流在收盘后主更新并安排晚间补跑', () => {
  const workflow = fs.readFileSync(path.join(projectRoot, '.github/workflows/update_data.yml'), 'utf8');

  assert.match(workflow, /cron: '30 9 \* \* 1-5'/);
  assert.match(workflow, /cron: '30 12 \* \* 1-5'/);
  assert.match(workflow, /python scheduled_update\.py --attempts 3 --base-delay 20/);
  assert.match(workflow, /timeout-minutes: 30/);
  assert.match(workflow, /permissions:\n\s+contents: write/);
  assert.match(workflow, /concurrency:/);
  assert.match(workflow, /git add live_data\.json strategy_presets\.json/);
});
