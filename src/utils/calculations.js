// src/utils/calculations.js
import {
  INSURANCE_STABILITY_CONFIG,
  PENSION_ANNUAL_MAX,
  PROPERTY_THRESHOLDS,
  STRESS_PRESETS,
  HISTORICAL_REPLAYS,
  BEHAVIOR_DRAWDOWN_MAP,
  BEHAVIOR_RULES,
  THERMOMETER_TIERS,
  LIQUIDITY_DISCOUNT_FACTOR,
  LIQUIDITY_SAFE_COVERAGE_RATIO,
  CONCENTRATION_LIMITS
} from '../constants.js';

/**
 * 资产配置看板核心指标测算
 */
export function calculateBoardMetrics(boardState) {
  const { principal, bufferSeed, targetMonthly, growthRate, assets } = boardState;
  const investPrincipal = Math.max(0, principal - bufferSeed); // 万元
  
  let totalWeight = 0;
  let blendedYield = 0;
  
  Object.values(assets).forEach(asset => {
    const w = (asset.weight || 0) / 100.0;
    const y = (asset.yield || 0) / 100.0;
    totalWeight += w;
    blendedYield += w * y;
  });

  const expectedAnnualDividend = investPrincipal * blendedYield * 10000; // 元
  const expectedMonthlyAvg = expectedAnnualDividend / 12.0; // 元
  const targetMonthlyYuan = targetMonthly * 10000; // 元
  const gapMonthly = targetMonthlyYuan - expectedMonthlyAvg;

  return {
    investPrincipal,
    totalWeight: totalWeight * 100,
    blendedYield: blendedYield * 100,
    growthRate,
    expectedAnnualDividend,
    expectedMonthlyAvg,
    targetMonthlyYuan,
    gapMonthly,
    isWeightValid: Math.abs(totalWeight - 1.0) < 0.001
  };
}

/**
 * 现金缓冲池 36 个月逐月平滑模拟推演 (基础推演引擎)
 */
export function calculateBufferSimulation(boardState, monthsRange = 36) {
  const { principal, bufferSeed, targetMonthly, moneyMarketRate, assets } = boardState;
  const investPrincipalYuan = Math.max(0, principal - bufferSeed) * 10000;
  const targetMonthlyWithdraw = targetMonthly * 10000;
  const mmRate = (moneyMarketRate || 2.0) / 100.0;

  let currentBuffer = bufferSeed * 10000;
  const timeline = [];
  let minBuffer = currentBuffer;
  let mostFragileMonth = 1;
  let totalDividends = 0;

  for (let t = 1; t <= monthsRange; t++) {
    const calendarMonth = ((t - 1) % 12) + 1;

    // 计算当月收到的分红
    let monthDividend = 0;
    Object.values(assets).forEach(asset => {
      const distRatio = (asset.months && asset.months[calendarMonth]) || 0;
      if (distRatio > 0) {
        const assetVal = investPrincipalYuan * ((asset.weight || 0) / 100.0);
        monthDividend += assetVal * ((asset.yield || 0) / 100.0) * distRatio;
      }
    });

    // 缓冲池利息 (期初余额计算)
    const monthInterest = Math.max(0, currentBuffer) * (mmRate / 12.0);
    // 期末余额
    const nextBuffer = currentBuffer + monthDividend + monthInterest - targetMonthlyWithdraw;

    if (currentBuffer < minBuffer) {
      minBuffer = currentBuffer;
      mostFragileMonth = t;
    }

    timeline.push({
      monthIndex: t,
      calendarMonth,
      startBuffer: currentBuffer,
      dividend: monthDividend,
      interest: monthInterest,
      withdraw: targetMonthlyWithdraw,
      endBuffer: nextBuffer
    });

    totalDividends += monthDividend;
    currentBuffer = nextBuffer;
  }

  return {
    timeline,
    minBuffer,
    mostFragileMonth,
    totalDividends,
    isBufferSafe: minBuffer >= 0
  };
}

/**
 * 目标推演终值与三大杠杆反解
 */
export function calculateGoalProjection({
  currentYear = 2026,
  targetYear,
  targetAmount,
  monthlySurplus,
  growthRate,
  currentPrincipal,
  reservedAmount = 0,
  safeRate = 2.0
}) {
  const years = Math.max(1, targetYear - currentYear);
  const months = years * 12;
  const rAnnual = (growthRate || 6.5) / 100.0;
  const rMonthly = rAnnual / 12.0;
  const rSafe = (safeRate || 2.0) / 100.0;

  // 1. 本金复利终值
  const fvPrincipal = currentPrincipal * Math.pow(1 + rAnnual, years);

  // 2. 月结余定投复利终值 (期初年金)
  let fvMonthly = 0;
  if (rMonthly > 0) {
    fvMonthly = monthlySurplus * ((Math.pow(1 + rMonthly, months) - 1) / rMonthly) * (1 + rMonthly);
  } else {
    fvMonthly = monthlySurplus * months;
  }

  // 3. 预留金额终值 (稳健计息)
  const fvReserved = reservedAmount * Math.pow(1 + rSafe, years);

  const fvTotal = fvPrincipal + fvMonthly + fvReserved;
  const diff = fvTotal - targetAmount;
  const isAchieved = diff >= 0;
  const gap = isAchieved ? 0 : Math.abs(diff);

  let levers = null;
  if (!isAchieved && gap > 0) {
    // 杠杆 1: 储蓄端 (每月需多储蓄 ΔPMT)
    let extraMonthly = 0;
    if (rMonthly > 0) {
      const annuityFactor = ((Math.pow(1 + rMonthly, months) - 1) / rMonthly) * (1 + rMonthly);
      extraMonthly = gap / annuityFactor;
    } else {
      extraMonthly = gap / months;
    }

    // 杠杆 2: 收益端 (反解所需年化收益率 reqRate)
    let reqRate = rAnnual;
    for (let iter = 0; iter < 100; iter++) {
      const mRate = reqRate / 12.0;
      const fvP = currentPrincipal * Math.pow(1 + reqRate, years);
      let fvM = 0;
      if (mRate > 0) {
        fvM = monthlySurplus * ((Math.pow(1 + mRate, months) - 1) / mRate) * (1 + mRate);
      } else {
        fvM = monthlySurplus * months;
      }
      const curFv = fvP + fvM + fvReserved;
      const fvDiff = curFv - targetAmount;
      if (Math.abs(fvDiff) < 1.0) break;

      const dfvP = currentPrincipal * years * Math.pow(1 + reqRate, Math.max(0, years - 1));
      const dfvM = monthlySurplus * months * Math.pow(1 + mRate, Math.max(0, months - 1));
      const dfv = dfvP + dfvM / 12.0;
      if (Math.abs(dfv) < 1e-6) break;
      reqRate = reqRate - fvDiff / dfv;
      if (reqRate < -0.5) { reqRate = -0.5; break; }
      if (reqRate > 2.0) { reqRate = 2.0; break; }
    }

    const reqRatePct = parseFloat((reqRate * 100).toFixed(2));
    const rateDiffPct = parseFloat(((reqRate - rAnnual) * 100).toFixed(2));
    const isRateSafe = reqRate <= 0.08;

    // 杠杆 3: 目标端 (放宽目标金额或延后年限)
    const loosenAmount = Math.round(gap);
    let delayYears = 0;
    for (let extraY = 1; extraY <= 30; extraY++) {
      const newY = years + extraY;
      const newM = newY * 12;
      const fvP = currentPrincipal * Math.pow(1 + rAnnual, newY);
      let fvM = 0;
      if (rMonthly > 0) {
        fvM = monthlySurplus * ((Math.pow(1 + rMonthly, newM) - 1) / rMonthly) * (1 + rMonthly);
      } else {
        fvM = monthlySurplus * newM;
      }
      const fvR = reservedAmount * Math.pow(1 + rSafe, newY);
      if (fvP + fvM + fvR >= targetAmount) {
        delayYears = extraY;
        break;
      }
    }
    if (delayYears === 0) delayYears = 30;

    levers = {
      extraMonthly: Math.round(extraMonthly),
      reqRatePct,
      rateDiffPct,
      isRateSafe,
      loosenAmount,
      delayYears,
      delayedTargetYear: targetYear + delayYears
    };
  }

  return {
    years,
    months,
    fvPrincipal,
    fvMonthly,
    fvReserved,
    fvTotal,
    diff,
    isAchieved,
    gap,
    levers
  };
}

/**
 * 提前退休全生命周期持久性检验 (至 85 岁，复用缓冲池季节性逻辑)
 */
export function simulateEarlyRetirement({
  currentAge = 35,
  retireAge = 50,
  targetAmount,
  projectedCapitalAtRetire,
  monthlyExpense = 10000,
  dividendYield = 4.8,
  bufferInterestRate = 2.0,
  endAge = 85
}) {
  const totalYears = Math.max(1, endAge - retireAge);
  const totalMonths = totalYears * 12;
  let capital = (projectedCapitalAtRetire && projectedCapitalAtRetire > 0) ? projectedCapitalAtRetire : targetAmount;
  let lowestCapital = capital;
  let mostFragileMonth = 1;
  let depletionMonth = null;
  let depletionAge = null;

  const seasonality = {
    1: 0.02, 2: 0.02, 3: 0.03, 4: 0.05,
    5: 0.15, 6: 0.25, 7: 0.30, 8: 0.10,
    9: 0.03, 10: 0.02, 11: 0.01, 12: 0.02
  };

  const annualDivRate = (dividendYield || 4.8) / 100.0;
  const mmRate = (bufferInterestRate || 2.0) / 100.0;
  const samplePoints = [];

  for (let m = 1; m <= totalMonths; m++) {
    const calendarMonth = ((m - 1) % 12) + 1;
    const currentAgeApprox = retireAge + (m - 1) / 12.0;

    const divWeight = seasonality[calendarMonth] || (1 / 12.0);
    const monthlyDiv = capital * annualDivRate * divWeight;
    const monthlyInterest = Math.max(0, capital) * (mmRate / 12.0);

    capital = capital + monthlyDiv + monthlyInterest - monthlyExpense;

    if (capital < lowestCapital) {
      lowestCapital = capital;
      mostFragileMonth = m;
    }

    if (capital <= 0 && depletionMonth === null) {
      depletionMonth = m;
      depletionAge = parseFloat(currentAgeApprox.toFixed(1));
    }

    if (m % 24 === 0 || m === 1 || m === totalMonths) {
      samplePoints.push({
        month: m,
        age: parseFloat(currentAgeApprox.toFixed(1)),
        capital: Math.max(0, Math.round(capital))
      });
    }
  }

  return {
    isSustainable: depletionMonth === null,
    finalCapital: Math.max(0, capital),
    depletionAge,
    depletionMonth,
    lowestCapital: Math.round(lowestCapital),
    mostFragileMonth,
    mostFragileAge: parseFloat((retireAge + (mostFragileMonth - 1) / 12.0).toFixed(1)),
    samplePoints
  };
}

/**
 * 债务决策对照与路径对比测算
 */
export function calculateDebtDecisionMetrics(debtState = {}, growthRate = 6.5) {
  const bracketMedians = {
    '<3.5%': 3.0,
    '3.5-4.5%': 4.0,
    '4.5-6%': 5.25,
    '>6%': 7.2
  };

  const bracket = debtState.debtRateBracket || '4.5-6%';
  const bracketMedian = bracketMedians[bracket] || 5.25;
  const effectiveDebtRate = typeof debtState.customDebtRate === 'number' && debtState.customDebtRate > 0
    ? debtState.customDebtRate
    : bracketMedian;

  const conservativeYield = parseFloat(((growthRate || 6.5) * 0.7).toFixed(2));

  let decisionType = 'neutral';
  let decisionText = '';

  if (effectiveDebtRate > conservativeYield + 2.0) {
    decisionType = 'repay_first';
    decisionText = '优先清偿高息债务（相当于获得无风险的利差收益）';
  } else if (effectiveDebtRate < conservativeYield - 2.0) {
    decisionType = 'invest_first';
    decisionText = '保持贷款、优先投资，但需确认现金流稳定性';
  } else {
    decisionType = 'neutral';
    decisionText = '两者皆可，优先级取决于风险偏好与流动性需求';
  }

  const hasHighInterestAlert = (debtState.highInterestDebtBalance > 0) || (bracket === '>6%') || (effectiveDebtRate > 6.0);

  const fundX = typeof debtState.availableFundX === 'number' && debtState.availableFundX > 0 
    ? debtState.availableFundX 
    : 200000;

  const rDebt = effectiveDebtRate / 100.0;
  const rInvest = conservativeYield / 100.0;

  const horizons = [3, 5, 10];
  const comparisonTable = horizons.map(years => {
    const fvRepay = fundX * Math.pow(1 + rDebt, years);
    const fvInvest = fundX * Math.pow(1 + rInvest, years);
    const diff = fvRepay - fvInvest;
    const diffPct = ((fvRepay - fvInvest) / fundX) * 100.0;

    let advantage = '持平';
    if (diff > 1) {
      advantage = '提前还贷更优';
    } else if (diff < -1) {
      advantage = '坚持投资更优';
    }

    return {
      years,
      fundX,
      fvRepay: Math.round(fvRepay),
      fvInvest: Math.round(fvInvest),
      diff: Math.round(diff),
      diffPct: parseFloat(diffPct.toFixed(2)),
      advantage
    };
  });

  const totalDebtBalance = (debtState.mortgageBalance || 0) + 
                           (debtState.carLoanBalance || 0) + 
                           (debtState.consumerLoanBalance || 0) + 
                           (debtState.businessLoanBalance || 0);

  return {
    bracket,
    bracketMedian,
    effectiveDebtRate,
    growthRate,
    conservativeYield,
    decisionType,
    decisionText,
    hasHighInterestAlert,
    fundX,
    comparisonTable,
    totalDebtBalance
  };
}

/**
 * 1. 家庭保障缺口测算 (责任缺口法)
 */
export function calculateInsuranceGap(healthState = {}, insuranceState = {}, totalDebtBalance = 0) {
  const monthlyEssential = healthState.essentialMonthlyExpense || (healthState.monthlyExpense ? healthState.monthlyExpense * 0.7 : 12000);
  const future10yExpense = monthlyEssential * 120; // 10年生活费底线
  const childEdu = insuranceState.childEduTarget !== undefined ? insuranceState.childEduTarget : 500000;
  const liquidAssets = (healthState.bucket1y || 0) + (healthState.bucket1To3y || 0) + (healthState.bucket3To5y || 0) + (healthState.bucket5yPlus || 0);
  
  // 寿险责任测算 = 全部债务 + 10年生活费 + 子女教育金 - 流动金融资产
  const lifeTarget = Math.max(0, totalDebtBalance + future10yExpense + childEdu - liquidAssets);
  const existingLife = insuranceState.existingLifeCover || 0;
  const lifeGap = Math.max(0, lifeTarget - existingLife);

  const annualIncome = (healthState.monthlyIncome || 30000) * 12;
  const lifeGapIncomeMultiple = annualIncome > 0 ? parseFloat((lifeGap / annualIncome).toFixed(1)) : 0;

  // 重疾缺口测算 = 行业稳定性联动 3-5 年税后收入 + 30-50万康复金
  const stability = insuranceState.stabilityTier || 'medium';
  const stabConfig = INSURANCE_STABILITY_CONFIG[stability] || INSURANCE_STABILITY_CONFIG.medium;
  const critTarget = stabConfig.years * annualIncome + stabConfig.medical;
  const existingCrit = insuranceState.existingCritCover || 0;
  const critGap = Math.max(0, critTarget - existingCrit);
  const critGapIncomeMultiple = annualIncome > 0 ? parseFloat((critGap / annualIncome).toFixed(1)) : 0;

  // 意外险建议额 = 寿险缺口 50%
  const accidentTarget = Math.round(lifeTarget * 0.5);
  const existingAccident = insuranceState.existingAccidentCover || 0;
  const accidentGap = Math.max(0, accidentTarget - existingAccident);
  const accidentGapIncomeMultiple = annualIncome > 0 ? parseFloat((accidentGap / annualIncome).toFixed(1)) : 0;

  const hasMillionMedical = Boolean(insuranceState.hasMillionMedical);
  const coverageTier = insuranceState.coverageTier || 'insufficient';

  // 警告与降级条件：自评为前两档 ('none' 或 'insufficient') 且存在净缺口
  const hasNetGap = (lifeGap > 0) || (critGap > 0) || (accidentGap > 0) || (!hasMillionMedical);
  const shouldWarnAndDowngrade = (coverageTier === 'none' || coverageTier === 'insufficient') && hasNetGap;

  return {
    lifeTarget,
    existingLife,
    lifeGap,
    lifeGapIncomeMultiple,
    critTarget,
    existingCrit,
    critGap,
    critGapIncomeMultiple,
    accidentTarget,
    existingAccident,
    accidentGap,
    accidentGapIncomeMultiple,
    hasMillionMedical,
    coverageTier,
    shouldWarnAndDowngrade,
    stabConfig,
    annualIncome
  };
}

/**
 * 4. 个人养老金税优检查
 */
export function calculatePensionTaxBenefit(pensionState = {}) {
  const hasAccount = Boolean(pensionState.hasAccount);
  const deposited = Math.min(PENSION_ANNUAL_MAX, Math.max(0, Number(pensionState.currentYearDeposited) || 0));
  const taxRate = typeof pensionState.marginalTaxRate === 'number' ? pensionState.marginalTaxRate : 0.20;
  
  const remainingQuota = Math.max(0, PENSION_ANNUAL_MAX - deposited);
  const isTaxBenefitLimited = taxRate <= 0.001;
  const annualTaxSavingsForegone = Math.round(remainingQuota * taxRate);
  const cumulative20ySavings = annualTaxSavingsForegone * 20;

  return {
    hasAccount,
    deposited,
    remainingQuota,
    taxRate,
    annualTaxSavingsForegone,
    cumulative20ySavings,
    isTaxBenefitLimited,
    guidanceText: "红利低波类基金的长期持有属性与养老金账户封闭期匹配，可优先在该账户内承载（不构成产品推荐）。"
  };
}

/**
 * 5. 房产集中度强化分析与买房首付校验
 */
export function calculateRealEstateRisk(propertyState = {}, healthState = {}, debtState = {}) {
  const propertyVal = Number(propertyState.totalEstimatedValue) || 0;
  const mortgage = Number(debtState.mortgageBalance) || 0;
  const propertyNet = Math.max(0, propertyVal - mortgage);

  const financialAssets = (healthState.bucket1y || 0) + 
                          (healthState.bucket1To3y || 0) + 
                          (healthState.bucket3To5y || 0) + 
                          (healthState.bucket5yPlus || 0);

  const totalAssets = propertyVal + financialAssets;
  const totalDebt = (debtState.mortgageBalance || 0) + 
                    (debtState.carLoanBalance || 0) + 
                    (debtState.consumerLoanBalance || 0) + 
                    (debtState.businessLoanBalance || 0);

  const totalNetWorth = Math.max(1, totalAssets - totalDebt);
  const financialNetWorth = Math.max(0, financialAssets - Math.max(0, totalDebt - mortgage));

  // 房产净资产比
  const realEstateRatio = parseFloat(((propertyNet / totalNetWorth) * 100).toFixed(1));

  let tier = 'green';
  let tierAdvice = '房产净资产比处于健康合理区间（<60%），流动性防线稳固。';
  if (realEstateRatio > PROPERTY_THRESHOLDS.yellowMax * 100) {
    tier = 'red';
    tierAdvice = '房产集中度过高（>75%），严重挤压流动性资产。不宜再增配房产，且需充分评估极端情况下二手房流动性折价与变现摩擦风险！';
  } else if (realEstateRatio >= PROPERTY_THRESHOLDS.greenMax * 100) {
    tier = 'yellow';
    tierAdvice = '房产净资产比偏高（60-75%），建议家庭新增储蓄优先流向高流动性金融资产，优化净资产抗风险弹性。';
  }

  // 购房首付核验
  const hasHousePlan = Boolean(healthState.hasHousePlan);
  const expectedDownPayment = Number(healthState.expectedDownPayment) || 0;
  const readyFunds = (healthState.bucket1To3y || 0) + (healthState.bucket1y || 0);
  const downPaymentGap = Math.max(0, expectedDownPayment - readyFunds);
  const isDownPaymentShort = hasHousePlan && (downPaymentGap > 0);

  // 房产估值下跌压力冲击
  const stressDropPct = typeof propertyState.stressDropPct === 'number' ? propertyState.stressDropPct : PROPERTY_THRESHOLDS.defaultStressDropPct;
  const propertyStressVal = propertyVal * (1 - stressDropPct / 100.0);
  const stressTotalAssets = propertyStressVal + financialAssets;
  const stressTotalNetWorth = Math.max(0, stressTotalAssets - totalDebt);
  const normalDebtToAsset = parseFloat(((totalDebt / Math.max(1, totalAssets)) * 100).toFixed(1));
  const stressDebtToAsset = parseFloat(((totalDebt / Math.max(1, stressTotalAssets)) * 100).toFixed(1));

  return {
    propertyVal,
    mortgage,
    propertyNet,
    financialAssets,
    totalAssets,
    totalDebt,
    totalNetWorth,
    financialNetWorth,
    realEstateRatio,
    tier,
    tierAdvice,
    hasHousePlan,
    expectedDownPayment,
    readyFunds,
    downPaymentGap,
    isDownPaymentShort,
    downPaymentWarning: "首付储备不足，请勿动用中长期投资组合本金博取短期首付！",
    stressDropPct,
    propertyStressVal,
    stressTotalAssets,
    stressTotalNetWorth,
    normalDebtToAsset,
    stressDebtToAsset
  };
}

/**
 * 9. 流动性硬隔离校验
 */
export function checkLiquiditySegregation(healthState = {}, boardPrincipalTenThousand = 50) {
  const boardPrincipalYuan = boardPrincipalTenThousand * 10000;
  const bucket1y = healthState.bucket1y || 0;
  const bucket1To3y = healthState.bucket1To3y || 0;
  const bucket3To5y = healthState.bucket3To5y || 0;
  const bucket5yPlus = healthState.bucket5yPlus || 0;
  
  const liquidFinancialAssets = bucket1y + bucket1To3y + bucket3To5y + bucket5yPlus;
  const discountFactor = LIQUIDITY_DISCOUNT_FACTOR;

  // 可投资上限 = 流动金融资产 - 12个月确定性支出*100% - 1至3年确定性支出*50%
  const investableCeiling = Math.max(0, liquidFinancialAssets - (bucket1y * 1.0) - (bucket1To3y * discountFactor));
  const isViolated = boardPrincipalYuan > investableCeiling;
  const excessAmount = Math.max(0, boardPrincipalYuan - investableCeiling);

  const shortTermExpenses = bucket1y + bucket1To3y;
  const coverageRatio = shortTermExpenses > 0 ? parseFloat((liquidFinancialAssets / shortTermExpenses).toFixed(2)) : 99.0;
  const isCoverageInsufficient = coverageRatio < LIQUIDITY_SAFE_COVERAGE_RATIO;

  return {
    boardPrincipalYuan,
    liquidFinancialAssets,
    bucket1y,
    bucket1To3y,
    discountFactor,
    investableCeiling,
    isViolated,
    excessAmount,
    coverageRatio,
    isCoverageInsufficient,
    warningText: "已侵入未来确定性支出，请先单独预留短期资金！",
    distinctionNote: "缓冲池平滑分红淡季与月度支取波动，流动性硬隔离保障未来 1-3 年刚性确定性支出，二者职责分明不可混用。"
  };
}

/**
 * 10. 三重集中度检查 (标的/市场与币种/策略风格)
 */
export function checkTripleConcentration(assets = {}) {
  const assetList = Object.entries(assets).map(([code, item]) => ({
    code,
    name: item.name,
    weight: item.weight || 0,
    market: item.market || 'A股',
    style: item.style || '其他'
  }));

  // 1. 标的集中度
  const sorted = [...assetList].sort((a, b) => b.weight - a.weight);
  const maxSingle = sorted[0] || { name: '无', weight: 0 };
  const top3Weight = sorted.slice(0, 3).reduce((acc, cur) => acc + cur.weight, 0);

  const isSingleWarn = maxSingle.weight > CONCENTRATION_LIMITS.singleAssetYellow;
  const isTop3Danger = top3Weight > CONCENTRATION_LIMITS.top3AssetsRed;

  let targetStatus = 'green';
  let targetAdvice = '标的权重分布分散均匀，单一资产黑天鹅风险可控。';
  if (isTop3Danger) {
    targetStatus = 'red';
    targetAdvice = `前三大标的合计权重达到 ${top3Weight.toFixed(1)}% (红灯>70%)，需防范极端踩踏，建议将过大仓位再平衡分流。`;
  } else if (isSingleWarn) {
    targetStatus = 'yellow';
    targetAdvice = `单一标的【${maxSingle.name}】权重达 ${maxSingle.weight.toFixed(1)}% (黄灯>40%)，个股/单基金黑天鹅对组合冲击显著，需谨慎加仓。`;
  }

  // 2. 市场与币种集中度
  const marketSums = {};
  assetList.forEach(a => {
    marketSums[a.market] = (marketSums[a.market] || 0) + a.weight;
  });
  let maxMarket = { market: 'A股', weight: 0 };
  Object.entries(marketSums).forEach(([m, w]) => {
    if (w > maxMarket.weight) maxMarket = { market: m, weight: w };
  });

  const isMarketAlert = maxMarket.weight > CONCENTRATION_LIMITS.marketCurrencyAlert;
  let marketStatus = isMarketAlert ? 'yellow' : 'green';
  let marketAdvice = isMarketAlert 
    ? `【${maxMarket.market}】资产占比高达 ${maxMarket.weight.toFixed(1)}% (>60%)，建议适度配置跨市场/跨币种标的以平抑单一宏观主权风险。`
    : '市场分布处于多市场均衡阶段，宏观流动性冲击分散性良好。';

  // 3. 策略风格集中度 (红利低波风格簇)
  let dividendStyleWeight = 0;
  assetList.forEach(a => {
    if (a.style === '红利低波') {
      dividendStyleWeight += a.weight;
    }
  });

  const isStyleAlert = dividendStyleWeight > CONCENTRATION_LIMITS.dividendStyleClusterAlert;
  let styleStatus = isStyleAlert ? 'yellow' : 'green';
  let styleAdvice = isStyleAlert
    ? `红利低波类标的权重合计达 ${dividendStyleWeight.toFixed(1)}% (>50%)，需注意银行/煤炭/交运等底层重仓行业的景气周期共振风险！`
    : '策略风格保持多元，红利低波与成长防守资产比例平衡。';

  return {
    targetStatus,
    targetAdvice,
    maxSingle,
    top3Weight,
    marketStatus,
    marketAdvice,
    maxMarket,
    styleStatus,
    styleAdvice,
    dividendStyleWeight
  };
}

/**
 * 7. 行为约束引擎 (风险自评硬约束与透明化归因)
 */
export function calculateBehavioralEquityCeiling(behaviorState = {}, assets = {}) {
  const bracket = behaviorState.drawdownBracket || '10-20%';
  const baseCeiling = BEHAVIOR_DRAWDOWN_MAP[bracket] || 55;

  const reaction = behaviorState.marketDropReaction || 'panic_sell';
  const panicDeduction = BEHAVIOR_RULES.panicReactionDeduction[reaction] || 0;
  const cashflowDeduction = behaviorState.cashflowRelianceHigh ? BEHAVIOR_RULES.cashflowRelianceDeduction : 0;
  const industryDeduction = behaviorState.industryVolatileHigh ? BEHAVIOR_RULES.industryVolatileDeduction : 0;

  const rawCeiling = baseCeiling - panicDeduction - cashflowDeduction - industryDeduction;
  const finalCeiling = Math.max(BEHAVIOR_RULES.floorProtection, rawCeiling);

  // 实际配置权益比例计算 (权益类股票与ETF)
  let actualEquityWeight = 0;
  Object.values(assets).forEach(a => {
    if (a.category === 'Equity' || a.type === 'ETF' || a.type === 'Stock') {
      actualEquityWeight += (a.weight || 0);
    }
  });

  const isExceeded = actualEquityWeight > finalCeiling;
  const excessWeight = Math.max(0, actualEquityWeight - finalCeiling);
  const implicitDrawdown = parseFloat((finalCeiling * BEHAVIOR_RULES.extremeEquityDrawdown).toFixed(1));

  // "为什么是这个数" 透明化扣减过程
  const breakdownList = [
    { label: `自评回撤档位 (${bracket}) 基础权益上限`, delta: `+${baseCeiling}%` }
  ];
  if (panicDeduction > 0) {
    breakdownList.push({ label: '市场大跌第一反应 (恐慌卖出/观望)', delta: `-${panicDeduction}%` });
  }
  if (cashflowDeduction > 0) {
    breakdownList.push({ label: '日常现金流高度依赖投资收益', delta: `-${cashflowDeduction}%` });
  }
  if (industryDeduction > 0) {
    breakdownList.push({ label: '行业波动大且失业恢复期预期>6个月', delta: `-${industryDeduction}%` });
  }
  if (rawCeiling < BEHAVIOR_RULES.floorProtection) {
    breakdownList.push({ label: `触发工具安全保护底线 (${BEHAVIOR_RULES.floorProtection}%)`, delta: '兜底提升' });
  }

  return {
    bracket,
    baseCeiling,
    panicDeduction,
    cashflowDeduction,
    industryDeduction,
    finalCeiling,
    actualEquityWeight,
    isExceeded,
    excessWeight,
    implicitDrawdown,
    breakdownList,
    warningText: "超出您的行为风险约束！您自评的心理抗跌能力与家庭现金流刚性，无法承载当前高比例权益波动。"
  };
}

/**
 * 8. 估值温度计与卖出侧再平衡信号
 */
export function calculateThermometerSignal(percentile = 50) {
  const val = Math.min(100, Math.max(0, percentile));
  let tier = THERMOMETER_TIERS[2]; // 默认中性

  for (const t of THERMOMETER_TIERS) {
    if (val >= t.min && val <= t.max) {
      tier = t;
      break;
    }
  }

  const isDeepLow = tier.code === 'deep_low';
  const isOverheated = tier.code === 'overheat';
  const isWarm = tier.code === 'warm';

  return {
    percentile: val,
    tier,
    isDeepLow,
    isOverheated,
    isWarm,
    actionAdvice: tier.action,
    rebalanceAdvice: isOverheated 
      ? '【过热卖出信号】建议按月度 3 次分批将成长类与过热标的再平衡回目标权重。'
      : (isWarm ? '【偏热信号】暂停增量追高，新增资金导向现金缓冲池。' : '【定投/持有信号】估值安全边际充裕，执行既定买入与持有纪律。')
  };
}

/**
 * 6. 复合情景风险压力测试 (完全复用 36 个月推演引擎并扩展失业、分红降、延迟、医疗与通胀)
 */
export function runCompoundStressTest(boardState = {}, stressScenario = {}, healthState = {}, monthsRange = 36) {
  const { principal, bufferSeed, targetMonthly, moneyMarketRate, assets } = boardState;
  const investPrincipalYuan = Math.max(0, principal - bufferSeed) * 10000;
  const mmRate = (moneyMarketRate || 2.0) / 100.0;

  // 情景参数解构
  const unemploymentMonths = stressScenario.unemploymentMonths || 0;
  const dividendDropRate = stressScenario.dividendDropRate || 0; // 如 30% -> 0.3
  const equityDrawdownRate = stressScenario.equityDrawdownRate || 0; // 如 20% -> 0.2
  const delayMonths = stressScenario.delayMonths || 0;
  const medicalExpense = stressScenario.medicalExpense || 0;
  const medicalMonth = stressScenario.medicalMonth || 6;
  const inflationRate = stressScenario.inflationRate || 0; // 如 5% 年通胀

  let currentBuffer = bufferSeed * 10000;
  const timeline = [];
  let minBuffer = currentBuffer;
  let exhaustionMonth = null;
  let maxDeficit = 0;

  for (let t = 1; t <= monthsRange; t++) {
    const calendarMonth = ((t - 1) % 12) + 1;

    // 通胀影响生活费支出逐月微增
    let monthlyWithdraw = targetMonthly * 10000;
    if (inflationRate > 0) {
      monthlyWithdraw = monthlyWithdraw * Math.pow(1 + inflationRate / 12.0, t);
    }

    // 失业期生活费增加（家庭月工资结余归零，完全靠缓冲池净流出）
    // （此处保持纯缓冲池生活费提取逻辑）

    // 突发医疗支出冲击
    let extraOutflow = 0;
    if (medicalExpense > 0 && t === medicalMonth) {
      extraOutflow = medicalExpense;
    }

    // 分红到账计算 (考虑延迟与降幅)
    let monthDividend = 0;
    const effectiveCalMonth = delayMonths > 0 ? ((((calendarMonth - 1 - delayMonths) % 12) + 12) % 12) + 1 : calendarMonth;

    Object.values(assets).forEach(asset => {
      const distRatio = (asset.months && asset.months[effectiveCalMonth]) || 0;
      if (distRatio > 0) {
        const assetVal = investPrincipalYuan * ((asset.weight || 0) / 100.0);
        const baseDiv = assetVal * ((asset.yield || 0) / 100.0) * distRatio;
        // 分红折减
        monthDividend += baseDiv * (1 - dividendDropRate);
      }
    });

    // 缓冲池闲置利息
    const monthInterest = Math.max(0, currentBuffer) * (mmRate / 12.0);

    const nextBuffer = currentBuffer + monthDividend + monthInterest - monthlyWithdraw - extraOutflow;

    if (currentBuffer < minBuffer) {
      minBuffer = currentBuffer;
    }
    if (nextBuffer < 0 && exhaustionMonth === null) {
      exhaustionMonth = t;
    }
    if (nextBuffer < 0 && Math.abs(nextBuffer) > maxDeficit) {
      maxDeficit = Math.abs(nextBuffer);
    }

    timeline.push({
      month: t,
      calendarMonth,
      startBuffer: Math.round(currentBuffer),
      dividend: Math.round(monthDividend),
      interest: parseFloat(monthInterest.toFixed(1)),
      withdraw: Math.round(monthlyWithdraw + extraOutflow),
      endBuffer: Math.round(nextBuffer)
    });

    currentBuffer = nextBuffer;
  }

  // 计算枯竭时需变现资产金额 (按折价后市值折算)
  // 如果回撤 35%，折算需卖出的名义本金 = maxDeficit / (1 - 0.35)
  const discountMultiplier = Math.max(0.1, 1 - equityDrawdownRate);
  const minAssetToSell = exhaustionMonth ? Math.round(maxDeficit / discountMultiplier) : 0;

  // 恢复安全水位所需月数估算 (假设压力解除后月均结余回填)
  const monthlySurplusYuan = healthState.monthlySurplus || 10000;
  const targetBufferTarget = bufferSeed * 10000;
  const deficitToFill = exhaustionMonth ? (targetBufferTarget + maxDeficit) : 0;
  const monthsToRecover = deficitToFill > 0 ? Math.ceil(deficitToFill / Math.max(1000, monthlySurplusYuan)) : 0;

  return {
    timeline,
    minBuffer: Math.round(minBuffer),
    exhaustionMonth,
    isExhausted: exhaustionMonth !== null,
    minAssetToSell,
    monthsToRecover,
    maxDeficit: Math.round(maxDeficit),
    equityDrawdownRate
  };
}

/**
 * 11. 评分可解释化 (脆弱性评分 & 理财进攻性因子构成拆解)
 */
export function calculateExplainableScores(state = {}) {
  const { board = {}, health = {}, debt = {}, insurance = {}, behavior = {} } = state;
  const boardMetrics = calculateBoardMetrics(board);
  const bufferSim = calculateBufferSimulation(board);
  const debtMetrics = calculateDebtDecisionMetrics(debt, board.growthRate);
  const insGap = calculateInsuranceGap(health, insurance, debtMetrics.totalDebtBalance);
  const liqCheck = checkLiquiditySegregation(health, board.principal);
  const behCheck = calculateBehavioralEquityCeiling(behavior, board.assets);

  // 一、脆弱性评分 (0 - 100 分，越低越稳健，高分代表高度脆弱)
  // 子因子 1: 债务杠杆因子 (0-30 分)
  let debtScore = 0;
  if (debtMetrics.hasHighInterestAlert) {
    debtScore = 30;
  } else if (debtMetrics.totalDebtBalance > 1000000) {
    debtScore = 20;
  } else if (debtMetrics.totalDebtBalance > 0) {
    debtScore = 10;
  }

  // 子因子 2: 流动性硬隔离与备用金覆盖 (0-30 分)
  let liqScore = 0;
  if (liqCheck.isViolated) {
    liqScore = 30;
  } else if (liqCheck.isCoverageInsufficient) {
    liqScore = 18;
  } else {
    liqScore = 5;
  }

  // 子因子 3: 保障缺口敞口 (0-25 分)
  let insScore = 0;
  if (insGap.shouldWarnAndDowngrade) {
    insScore = 25;
  } else if (insGap.lifeGap > 0 || insGap.critGap > 0) {
    insScore = 15;
  } else {
    insScore = 0;
  }

  // 子因子 4: 缓冲池平滑安全度 (0-15 分)
  let bufScore = 0;
  if (!bufferSim.isBufferSafe) {
    bufScore = 15;
  } else if (bufferSim.minBuffer < 20000) {
    bufScore = 8;
  } else {
    bufScore = 0;
  }

  const totalVulnerability = debtScore + liqScore + insScore + bufScore;

  // 寻找拖后腿因子
  const vulnFactors = [
    { name: '高息与综合债务杠杆', score: debtScore, max: 30 },
    { name: '流动性硬隔离与短期覆盖', score: liqScore, max: 30 },
    { name: '家庭保障缺口与医疗兜底', score: insScore, max: 25 },
    { name: '现金缓冲池淡旺季平滑', score: bufScore, max: 15 }
  ];
  vulnFactors.sort((a, b) => (b.score / b.max) - (a.score / a.max));
  const worstVulnFactor = vulnFactors[0];

  // 二、理财进攻性评分 (0 - 100 分，反映组合风险博取偏好)
  // 子因子 1: 权益类资产仓位 (0-40 分)
  const equityWeight = behCheck.actualEquityWeight;
  const eqScore = Math.min(40, Math.round((equityWeight / 100.0) * 40));

  // 子因子 2: 预期收益率进取度 (0-30 分)
  const gRate = board.growthRate || 6.5;
  const growthScore = Math.min(30, Math.round((Math.max(0, gRate - 3.0) / 7.0) * 30));

  // 子因子 3: 行为约束超限博取 (0-30 分)
  const behExceedScore = behCheck.isExceeded ? Math.min(30, Math.round(behCheck.excessWeight * 1.5)) : 5;

  const totalAggressiveness = Math.min(100, eqScore + growthScore + behExceedScore);

  return {
    totalVulnerability,
    vulnerabilityLevel: totalVulnerability > 60 ? '高危脆弱' : (totalVulnerability > 35 ? '中度脆弱' : '稳健安全'),
    vulnFactors,
    worstVulnConclusion: `本期【${worstVulnFactor.name}】得分为 ${worstVulnFactor.score}分 (满分${worstVulnFactor.max}分)，是推高家庭财务脆弱性的首要短板。`,
    totalAggressiveness,
    aggressivenessLevel: totalAggressiveness > 70 ? '激进进攻' : (totalAggressiveness > 40 ? '平衡进取' : '谨慎保守'),
    aggFactors: [
      { name: '权益类持仓权重', score: eqScore, max: 40 },
      { name: '增长预期收益率目标', score: growthScore, max: 30 },
      { name: '超越行为约束博取度', score: behExceedScore, max: 30 }
    ]
  };
}

/**
 * 11. 统一风险仪表盘 (汇聚 6 大红黄绿灯风险源)
 */
export function calculateUnifiedRiskDashboard(state = {}) {
  const { board = {}, health = {}, debt = {}, insurance = {}, behavior = {} } = state;
  const debtMetrics = calculateDebtDecisionMetrics(debt, board.growthRate);
  const insGap = calculateInsuranceGap(health, insurance, debtMetrics.totalDebtBalance);
  const liqCheck = checkLiquiditySegregation(health, board.principal);
  const bufferSim = calculateBufferSimulation(board);
  const concentration = checkTripleConcentration(board.assets);
  const behCheck = calculateBehavioralEquityCeiling(behavior, board.assets);

  const lights = [
    {
      id: 'high_interest_debt',
      name: '高息与综合债务',
      targetTab: 'health',
      targetAnchor: 'debt-decision-card',
      level: debtMetrics.hasHighInterestAlert ? 'red' : (debtMetrics.totalDebtBalance > 0 ? 'yellow' : 'green'),
      desc: debtMetrics.hasHighInterestAlert 
        ? '存在高息债务或利率>6%，刚性侵蚀资产！' 
        : (debtMetrics.totalDebtBalance > 0 ? '存在常规负债，利差在可控范围' : '零负债，资产轻盈'),
      advice: debtMetrics.decisionText
    },
    {
      id: 'liquidity_isolation',
      name: '流动性硬隔离',
      targetTab: 'board',
      targetAnchor: 'liquidity-isolation-card',
      level: liqCheck.isViolated ? 'red' : (liqCheck.isCoverageInsufficient ? 'yellow' : 'green'),
      desc: liqCheck.isViolated 
        ? `可用本金超限 ¥${Math.round(liqCheck.excessAmount).toLocaleString()}元，已侵入短期刚需！`
        : (liqCheck.isCoverageInsufficient ? `短期支出覆盖倍数 ${liqCheck.coverageRatio}x 偏低` : '1-3年确定支出已严密隔离'),
      advice: liqCheck.isViolated ? liqCheck.warningText : '保持短期资金与投资资金硬隔离'
    },
    {
      id: 'insurance_protection',
      name: '家庭基础保障',
      targetTab: 'health',
      targetAnchor: 'insurance-gap-card',
      level: insGap.shouldWarnAndDowngrade ? 'red' : ((insGap.lifeGap > 0 || insGap.critGap > 0) ? 'yellow' : 'green'),
      desc: insGap.shouldWarnAndDowngrade 
        ? '保障自评不足且存在重疾/寿险净缺口，抗风险脆弱！'
        : (!insGap.hasMillionMedical ? '缺少百万医疗险大额兜底' : '保障较为齐备'),
      advice: insGap.shouldWarnAndDowngrade ? '先补保障再配置，资产配置已降级为参考' : '按需逐步补齐缺口保额'
    },
    {
      id: 'buffer_safety',
      name: '缓冲池平滑',
      targetTab: 'buffer',
      targetAnchor: 'buffer-simulation-card',
      level: !bufferSim.isBufferSafe ? 'red' : (bufferSim.minBuffer < 20000 ? 'yellow' : 'green'),
      desc: !bufferSim.isBufferSafe 
        ? `第 ${bufferSim.mostFragileMonth} 个月出现亏空断流！` 
        : `36个月最低水位 ¥${Math.round(bufferSim.minBuffer).toLocaleString()}元`,
      advice: !bufferSim.isBufferSafe ? '需增加初始种子金或削减月生活费' : '淡旺季现金流平滑成功'
    },
    {
      id: 'portfolio_concentration',
      name: '三重集中度',
      targetTab: 'board',
      targetAnchor: 'concentration-card',
      level: (concentration.targetStatus === 'red' || concentration.marketStatus === 'red' || concentration.styleStatus === 'red') ? 'red' : (
        (concentration.targetStatus === 'yellow' || concentration.marketStatus === 'yellow' || concentration.styleStatus === 'yellow') ? 'yellow' : 'green'
      ),
      desc: concentration.targetStatus === 'red' 
        ? `前三标的占比达 ${concentration.top3Weight.toFixed(1)}%`
        : (concentration.styleStatus === 'yellow' ? `红利低波风格达 ${concentration.dividendStyleWeight.toFixed(1)}%` : '资产分散度良好'),
      advice: concentration.targetAdvice
    },
    {
      id: 'behavior_constraint',
      name: '行为风险约束',
      targetTab: 'board',
      targetAnchor: 'behavior-constraint-card',
      level: behCheck.isExceeded ? 'red' : 'green',
      desc: behCheck.isExceeded 
        ? `实际权益 ${behCheck.actualEquityWeight.toFixed(1)}% 超过行为约束上限 (${behCheck.finalCeiling}%)`
        : `权益仓位符合心理与现金流约束 (上限 ${behCheck.finalCeiling}%)`,
      advice: behCheck.isExceeded ? behCheck.warningText : '资产配置与情绪抗性相匹配'
    }
  ];

  const redCount = lights.filter(l => l.level === 'red').length;
  const yellowCount = lights.filter(l => l.level === 'yellow').length;
  const greenCount = lights.filter(l => l.level === 'green').length;

  return {
    lights,
    redCount,
    yellowCount,
    greenCount,
    overallHealth: redCount === 0 ? (yellowCount <= 1 ? '健康' : '关注') : '高风险'
  };
}
