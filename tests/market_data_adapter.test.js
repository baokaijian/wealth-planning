const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const modulePromise = import(pathToFileURL(
  path.resolve(__dirname, '../src/utils/marketDataAdapter.js')
).href);

test('资产适配器覆盖完整资产清单并优先使用验证后的收益率', async () => {
  const { buildAssetsFromMarketData } = await modulePromise;
  const assets = buildAssetsFromMarketData([
    {
      code: '510300', name: '沪深300 ETF', type: 'ETF', role: 'domestic_beta',
      market: 'CN', weight: 8, estimated_yield: 1.5,
      distribution_months: { 12: 1 }, target_index_code: '000300'
    },
    {
      code: '518880', name: '黄金 ETF', type: 'ETF', role: 'gold_hedge',
      market: 'CN', weight: 6, estimated_yield: 0, distribution_months: {}
    }
  ], {
    status: 'success',
    data: {
      '510300': {
        price: 4.21, yield: 2.31, price_as_of: '2026-10-08 15:00:00',
        distribution_as_of: '2026-06-30', distribution_months: { 6: 1 },
        yield_method: 'trailing_12m_cash_distributions'
      }
    }
  }, { '510300': { weight: 12 }, '518880': { weight: 88 } });

  assert.deepEqual(Object.keys(assets), ['510300', '518880']);
  assert.equal(assets['510300'].weight, 12);
  assert.equal(assets['510300'].yield, 2.31);
  assert.equal(assets['510300'].price, 4.21);
  assert.equal(assets['510300'].dataQuality, 'verified_trailing');
  assert.deepEqual(assets['510300'].months, { 6: 1 });
  assert.equal(assets['518880'].yield, 0);
  assert.equal(assets['518880'].bucket, 'hedge');
  assert.equal(assets['518880'].targetIndexCode, null);
});

test('旧版资产池与新版代码集合不一致时使用当前基准权重，避免叠加超过100%', async () => {
  const { buildAssetsFromMarketData } = await modulePromise;
  const configs = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../assets.json'), 'utf8'));
  const oldAssets = {
    '511880': { weight: 15 }, '511360': { weight: 15 }, '512890': { weight: 20 },
    '515450': { weight: 15 }, '513530': { weight: 10 }, '510300': { weight: 10 },
    '518880': { weight: 7 }, '511010': { weight: 8 }
  };
  const assets = buildAssetsFromMarketData(configs, {}, oldAssets);

  assert.equal(Object.values(assets).reduce((sum, asset) => sum + asset.weight, 0), 100);
  assert.equal(assets['511880'].weight, configs.find(item => item.code === '511880').weight);
  assert.equal('515450' in assets, false);
});

test('同一资产池的异常本地权重也回退到100%基准配置', async () => {
  const { buildAssetsFromMarketData } = await modulePromise;
  const configs = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../assets.json'), 'utf8'));
  const invalidExisting = Object.fromEntries(configs.map(item => [item.code, { weight: item.weight }]));
  invalidExisting['511880'].weight += 38;
  const assets = buildAssetsFromMarketData(configs, {}, invalidExisting);

  assert.equal(Object.values(assets).reduce((sum, asset) => sum + asset.weight, 0), 100);
  assert.equal(assets['511880'].weight, configs.find(item => item.code === '511880').weight);
});

test('估值适配器补齐 PE/PB/股息率及历史百分位', async () => {
  const { buildValuationIndices } = await modulePromise;
  const indices = buildValuationIndices([
    { date: '2026-01-01', index_code: '000300', pe: 10, pb: 1.1, dividend_yield: 3 },
    { date: '2026-10-08', index_code: '000300', pe: 15, pb: 1.6, dividend_yield: 2, pe_percentile_3y: 80, pb_percentile_3y: 70, dividend_yield_percentile_3y: 20 }
  ], [{ code: '000300', name: '沪深300', type: 'broad', defaultPercentile: 50 }]);

  assert.equal(indices[0].pe, 15);
  assert.equal(indices[0].pb, 1.6);
  assert.equal(indices[0].dividendYield, 2);
  assert.equal(indices[0].pePercentile, 80);
  assert.equal(indices[0].pbPercentile, 70);
  assert.equal(indices[0].defaultPercentile, 75);
  assert.equal(indices[0].valuationAsOf, '2026-10-08');
});

test('仓库真实资产与行情缓存可完整转换且权重保持100%', async () => {
  const { buildAssetsFromMarketData } = await modulePromise;
  const configs = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../assets.json'), 'utf8'));
  const live = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../live_data.json'), 'utf8'));
  const assets = buildAssetsFromMarketData(configs, live, {});

  assert.equal(Object.keys(assets).length, configs.length);
  assert.equal(Object.values(assets).reduce((sum, asset) => sum + asset.weight, 0), 100);
  assert.ok(Object.values(assets).every(asset => Number.isFinite(asset.yield)));
  assert.ok(Object.values(assets).every(asset => asset.bucket && asset.category));
});

test('估值缓存超过21天时保留PE/PB展示但禁用择时信号', async () => {
  const { buildValuationIndices } = await modulePromise;
  const indices = buildValuationIndices([
    { date: '2026-07-20', index_code: '000300', pe: 14.3, pb: 1.46, dividend_yield: 2.74, pe_percentile_3y: 88, pb_percentile_3y: 78, dividend_yield_percentile_3y: 8 }
  ], [{ code: '000300', name: '沪深300', type: 'broad', defaultPercentile: 30 }], new Date('2026-10-08T00:00:00'));

  assert.equal(indices[0].isStale, true);
  assert.equal(indices[0].defaultPercentile, 50);
  assert.equal(indices[0].rawPercentile, 83);
  assert.equal(indices[0].pe, 14.3);
  assert.equal(indices[0].pb, 1.46);
});
