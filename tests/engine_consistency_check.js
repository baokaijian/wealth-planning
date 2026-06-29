const fs = require('fs');
const path = require('path');
const engine = require('../portfolio_engine.js');

const repoRoot = path.resolve(__dirname, '..');
const casesPath = process.argv[2] || path.join(__dirname, 'engine_consistency_cases.json');
const assetsList = JSON.parse(fs.readFileSync(path.join(repoRoot, 'assets.json'), 'utf8'));
const cases = JSON.parse(fs.readFileSync(casesPath, 'utf8'));

function buildAssets() {
  const assets = {};
  assetsList.forEach((item) => {
    assets[item.code] = {
      ...item,
      yield: item.estimated_yield,
      price: 0.0,
      months: item.distribution_months || {},
      distribution_months: item.distribution_months || {},
    };
  });
  return assets;
}

function familyMetrics(fd) {
  const totalAssets = fd['ast-cash'] + fd['ast-mmf'] + fd['ast-ashare'] + fd['ast-hk'] +
    fd['ast-overseas'] + fd['ast-gold'] + fd['ast-house'] + fd['ast-insurance'] + fd['ast-others'];
  const totalLiabilities = fd['debt-house'] + fd['debt-car'] + fd['debt-consumption'] + fd['debt-biz'];
  const netWorth = totalAssets - totalLiabilities;
  const leverage = totalAssets > 0 ? totalLiabilities / totalAssets : 0.0;
  const repayIncomeRatio = fd['f-monthly-income'] > 0 ? fd['debt-monthly-repay'] / fd['f-monthly-income'] : 0.0;
  const surplusRatio = fd['f-monthly-income'] > 0 ? fd['f-surplus-income'] / fd['f-monthly-income'] : 0.0;
  const liquidCash = fd['ast-cash'] + fd['ast-mmf'];
  const monthlyEssential = Math.max(fd['f-essential-expense'], fd['f-fixed-expense'] * 0.7, 1.0);
  const cashCoverageMonths = liquidCash / (monthlyEssential + fd['debt-monthly-repay']);
  const investableAssets = fd['ast-cash'] + fd['ast-mmf'] + fd['ast-ashare'] + fd['ast-hk'] +
    fd['ast-overseas'] + fd['ast-gold'] + fd['ast-others'];
  return { totalAssets, netWorth, leverage, repayIncomeRatio, surplusRatio, cashCoverageMonths, investableAssets };
}

function runCase(testCase) {
  const assets = buildAssets();
  const weights = {};
  Object.entries(assets).forEach(([code, asset]) => {
    weights[code] = asset.weight;
  });
  const withdraw = testCase.targetMonthlyWan * 10000.0;
  const moneyRate = testCase.moneyMarketRatePct / 100.0;
  const feasibility = engine.calculateCashflowFeasibility(
    36,
    withdraw,
    testCase.bufferSeed,
    testCase.principal,
    weights,
    assets,
    moneyRate,
    testCase.startMonth,
    testCase.stableIncomeDrop,
    testCase.delayMonths,
    testCase.pauseDividendYear
  );
  const stress = engine.runStressTest(
    weights,
    assets,
    Math.max(testCase.principal - testCase.bufferSeed, 0.0),
    withdraw,
    testCase.stressBufferMonths,
    moneyRate,
    testCase.stressParams
  );
  const fm = familyMetrics(testCase.familyData);
  const family = engine.evaluateFamilyProfile(
    testCase.familyData,
    fm.investableAssets,
    fm.netWorth,
    fm.totalAssets,
    fm.leverage,
    fm.repayIncomeRatio,
    fm.surplusRatio,
    fm.cashCoverageMonths,
    [],
    parseFloat(testCase.familyData['inv-drawdown']) || 10
  );
  return {
    name: testCase.name,
    safeMonthlyWithdrawWan: feasibility.safeMonthlyWithdrawWan,
    healthScore: family.fourMoney.score,
    breachedAtMonth: stress.breachedAtMonth,
    minStressedBuffer: stress.minStressedBuffer,
  };
}

console.log(JSON.stringify(cases.map(runCase), null, 2));
