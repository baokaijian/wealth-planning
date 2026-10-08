// 将仓库内可定时更新的 JSON 数据转换成静态 React 页面使用的稳定契约。

const ROLE_META = {
  cash: { category: 'Cash', bucket: 'safety', style: '现金管理' },
  stable_income: { category: 'Bond', bucket: 'safety', style: '稳健固收' },
  long_duration_bond: { category: 'Bond', bucket: 'hedge', style: '利率长债' },
  dividend_income: { category: 'Equity', bucket: 'growth', style: '红利现金流' },
  domestic_beta: { category: 'Equity', bucket: 'growth', style: 'A股宽基' },
  tech_growth: { category: 'Equity', bucket: 'growth', style: '科技成长' },
  global_growth: { category: 'Equity', bucket: 'growth', style: '全球成长' },
  overseas_broad: { category: 'Equity', bucket: 'growth', style: '海外宽基' },
  overseas_tech: { category: 'Equity', bucket: 'growth', style: '海外科技' },
  small_cap: { category: 'Equity', bucket: 'growth', style: '小盘风险溢价' },
  china_offshore_growth: { category: 'Equity', bucket: 'growth', style: '离岸中国成长' },
  gold_hedge: { category: 'Gold', bucket: 'hedge', style: '黄金对冲' },
  hedge: { category: 'Gold', bucket: 'hedge', style: '黄金对冲' },
  bond_duration: { category: 'Bond', bucket: 'hedge', style: '利率长债' },
  reit_income: { category: 'REIT', bucket: 'growth', style: '公募REITs' },
  cashflow_alt: { category: 'REIT', bucket: 'growth', style: '另类现金流' },
};

function finiteOr(value, fallback = 0) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function finiteOrNull(value) {
  if (value === null || value === undefined || value === '') return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function marketLabel(market) {
  return { CN: 'A股', HK: '港股', US: '美股', GLOBAL: '全球' }[market] || market || '其他';
}

export function buildAssetsFromMarketData(assetConfigs = [], livePayload = {}, existingAssets = {}) {
  const liveData = livePayload?.data || {};
  const configs = Array.isArray(assetConfigs) ? assetConfigs : [];
  const configCodes = configs.map(config => config?.code).filter(Boolean).sort();
  const existingCodes = Object.keys(existingAssets || {}).sort();
  const existingWeightTotal = Object.values(existingAssets || {}).reduce(
    (sum, asset) => sum + finiteOr(asset?.weight, 0),
    0
  );
  const preserveExistingWeights = configCodes.length === existingCodes.length
    && configCodes.every((code, index) => code === existingCodes[index])
    && Math.abs(existingWeightTotal - 100) <= 0.01;
  return configs.reduce((result, config) => {
    if (!config?.code) return result;
    const live = liveData[config.code] || {};
    const existing = existingAssets[config.code] || {};
    const role = ROLE_META[config.role] || { category: 'Other', bucket: 'growth', style: config.role || '其他' };
    const liveYield = Number(live.yield);
    const hasVerifiedYield = Number.isFinite(liveYield) && liveYield >= 0;
    const liveMonths = live.distribution_months && Object.keys(live.distribution_months).length > 0
      ? live.distribution_months
      : null;
    result[config.code] = {
      ...existing,
      name: config.name,
      type: config.type || 'ETF',
      weight: preserveExistingWeights
        ? (existing.weight ?? finiteOr(config.weight, 0))
        : finiteOr(config.weight, 0),
      yield: hasVerifiedYield ? liveYield : finiteOr(config.estimated_yield, 0),
      months: liveMonths || config.distribution_months || {},
      market: marketLabel(config.market),
      category: role.category,
      style: role.style,
      bucket: role.bucket,
      targetIndexCode: config.target_index_code || null,
      price: Number.isFinite(Number(live.price)) ? Number(live.price) : null,
      priceAsOf: live.price_as_of || config.price_as_of || '',
      yieldAsOf: live.distribution_as_of || config.distribution_as_of || '',
      yieldMethod: hasVerifiedYield ? live.yield_method : config.yield_method,
      dataQuality: hasVerifiedYield ? 'verified_trailing' : 'planning_assumption',
      strategyNote: config.strategy_note || '',
      riskNote: config.risk_note || ''
    };
    return result;
  }, {});
}

function latestRowsByCode(history = []) {
  const latest = new Map();
  for (const row of Array.isArray(history) ? history : []) {
    if (!row?.index_code || !row?.date) continue;
    const previous = latest.get(row.index_code);
    if (!previous || row.date > previous.date) latest.set(row.index_code, row);
  }
  return latest;
}

function percentile(values, value) {
  const finite = values.map(Number).filter(Number.isFinite).sort((a, b) => a - b);
  if (!finite.length || !Number.isFinite(Number(value))) return null;
  const count = finite.filter(item => item <= Number(value)).length;
  return Math.round((count / finite.length) * 1000) / 10;
}

export function buildValuationIndices(history = [], baseIndices = [], referenceDate = new Date()) {
  const latest = latestRowsByCode(history);
  const rowsByCode = (Array.isArray(history) ? history : []).reduce((result, row) => {
    if (!row?.index_code) return result;
    (result[row.index_code] ||= []).push(row);
    return result;
  }, {});

  return (Array.isArray(baseIndices) ? baseIndices : []).map(base => {
    const row = latest.get(base.code);
    if (!row) return base;
    const peers = rowsByCode[base.code] || [];
    const hasSufficientHistory = !String(row.percentile_window || '').startsWith('insufficient_history');
    const pePercentile = hasSufficientHistory
      ? (finiteOrNull(row.pe_percentile_3y) ?? percentile(peers.map(item => item.pe), row.pe))
      : null;
    const pbPercentile = hasSufficientHistory
      ? (finiteOrNull(row.pb_percentile_3y) ?? percentile(peers.map(item => item.pb), row.pb))
      : null;
    const yieldPercentile = hasSufficientHistory
      ? (finiteOrNull(row.dividend_yield_percentile_3y) ?? percentile(peers.map(item => item.dividend_yield), row.dividend_yield))
      : null;
    const defaultPercentile = !hasSufficientHistory
      ? 50
      : base.type === 'dividend'
      ? yieldPercentile
      : Math.round(((pePercentile + pbPercentile) / 2) * 10) / 10;
    const asOfDate = new Date(`${row.date}T00:00:00`);
    const reference = referenceDate instanceof Date ? referenceDate : new Date(referenceDate);
    const staleDays = Number.isFinite(asOfDate.getTime()) && Number.isFinite(reference.getTime())
      ? Math.max(0, Math.floor((reference.getTime() - asOfDate.getTime()) / 86400000))
      : null;
    const isStale = staleDays !== null && staleDays > 21;
    return {
      ...base,
      pe: finiteOr(row.pe, base.pe),
      pb: finiteOr(row.pb, base.pb ?? 0),
      dividendYield: finiteOr(row.dividend_yield, base.dividendYield),
      pePercentile,
      pbPercentile,
      dividendYieldPercentile: yieldPercentile,
      defaultPercentile: isStale ? 50 : defaultPercentile,
      rawPercentile: defaultPercentile,
      hasSufficientHistory,
      isStale,
      staleDays,
      valuationAsOf: row.date,
      valuationDataTime: row.data_time || null,
      percentileWindow: row.percentile_window || 'local_history',
      valuationSource: row.valuation_source || 'local_history'
    };
  });
}
