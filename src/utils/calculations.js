// src/utils/calculations.js
import {
  INSURANCE_STABILITY_CONFIG,
  PENSION_ANNUAL_MAX,
  PROPERTY_THRESHOLDS,
  STRESS_PRESETS,
  HISTORICAL_REPLAYS,
  BEHAVIOR_DRAWDOWN_MAP,
  BEHAVIOR_RULES,
  THERMOMETER_INDICES,
  THERMOMETER_TIERS,
  LIQUIDITY_DISCOUNT_FACTOR,
  LIQUIDITY_SAFE_COVERAGE_RATIO,
  CONCENTRATION_LIMITS
} from '../constants.js';

/**
 * 资产配置看板核心指标测算
 */
export function calculateBoardMetrics(boardState) {
  const { principal, bufferSeed, targetMonthly, growthRate, assets = {} } = boardState;
  const investPrincipal = Math.max(0, principal - bufferSeed); // 万元
  
  let totalWeight = 0;
  let blendedYield = 0;
  
  Object.values(assets).forEach(asset => {
    const w = (asset.weight || 0) / 100.0;
    const y = (asset.yield || 0) / 100.0;
    totalWeight += w;
    blendedYield += w * y;
  });

  const totalWeightPct = parseFloat((totalWeight * 100).toFixed(2));
  const isWeightValid = Math.abs(totalWeightPct - 100.0) < 0.01;

  const expectedAnnualDividend = investPrincipal * blendedYield * 10000; // 元
  const expectedMonthlyAvg = expectedAnnualDividend / 12.0; // 元
  const targetMonthlyYuan = (targetMonthly || 1.2) * 10000; // 元
  const gapMonthly = targetMonthlyYuan - expectedMonthlyAvg;

  return {
    investPrincipal,
    totalWeight: totalWeightPct,
    blendedYield: parseFloat((blendedYield * 100).toFixed(2)),
    growthRate,
    expectedAnnualDividend: Math.round(expectedAnnualDividend),
    expectedMonthlyAvg: Math.round(expectedMonthlyAvg),
    targetMonthlyYuan: Math.round(targetMonthlyYuan),
    gapMonthly: Math.round(gapMonthly),
    isWeightValid
  };
}

/**
 * 现金缓冲池 36 个月逐月平滑模拟推演 (基础推演引擎)
 */
export function calculateBufferSimulation(boardState, monthsRange = 36) {
  const { principal, bufferSeed, targetMonthly, moneyMarketRate, assets = {} } = boardState;
  const investPrincipalYuan = Math.max(0, principal - bufferSeed) * 10000;
  const targetMonthlyWithdraw = (targetMonthly || 1.2) * 10000;
  const mmRate = (moneyMarketRate || 2.0) / 100.0;

  let currentBuffer = bufferSeed * 10000;
  const timeline = [];
  let minBuffer = currentBuffer;
  let mostFragileMonth = 1;
  let totalDividends = 0;

  for (let t = 1; t <= monthsRange; t++) {
    const calendarMonth = ((t - 1) % 12) + 1;

    let monthDividend = 0;
    Object.values(assets).forEach(asset => {
      const distRatio = (asset.months && asset.months[calendarMonth]) || 0;
      if (distRatio > 0) {
        const assetVal = investPrincipalYuan * ((asset.weight || 0) / 100.0);
        monthDividend += assetVal * ((asset.yield || 0) / 100.0) * distRatio;
      }
    });

    const monthInterest = Math.max(0, currentBuffer) * (mmRate / 12.0);
    const nextBuffer = currentBuffer + monthDividend + monthInterest - targetMonthlyWithdraw;

    if (currentBuffer < minBuffer) {
      minBuffer = currentBuffer;
      mostFragileMonth = t;
    }

    timeline.push({
      monthIndex: t,
      calendarMonth,
      startBuffer: Math.round(currentBuffer),
      dividend: Math.round(monthDividend),
      interest: parseFloat(monthInterest.toFixed(1)),
      withdraw: Math.round(targetMonthlyWithdraw),
      endBuffer: Math.round(nextBuffer)
    });

    totalDividends += monthDividend;
    currentBuffer = nextBuffer;
  }

  const isBufferSafe = minBuffer >= 0;
  return {
    timeline,
    minBuffer: Math.round(minBuffer),
    mostFragileMonth,
    totalDividends: Math.round(totalDividends),
    isBufferSafe,
    averageMonthlyDividend: Math.round(totalDividends / monthsRange)
  };
}

/**
 * 单个目标推演与三大杠杆反解
 */
export function calculateGoalProjection({
  currentYear = 2026,
  targetYear,
  targetAmount,
  monthlySurplus,
  growthRate = 6.5,
  currentPrincipal = 0,
  reservedAmount = 0,
  safeRate = 0.02
}) {
  const years = Math.max(1, targetYear - currentYear);
  const months = years * 12;
  const rAnnual = (growthRate || 6.5) / 100.0;
  const rMonthly = rAnnual / 12.0;

  const fvPrincipal = currentPrincipal * Math.pow(1 + rAnnual, years);

  let fvMonthly = 0;
  if (rMonthly > 0) {
    fvMonthly = monthlySurplus * ((Math.pow(1 + rMonthly, months) - 1) / rMonthly) * (1 + rMonthly);
  } else {
    fvMonthly = monthlySurplus * months;
  }

  const fvReserved = reservedAmount * Math.pow(1 + safeRate, years);
  const fvTotal = fvPrincipal + fvMonthly + fvReserved;
  const diff = fvTotal - targetAmount;
  const isAchieved = diff >= 0;
  const gap = Math.max(0, -diff);

  let levers = null;
  if (gap > 0) {
    let extraMonthly = 0;
    if (rMonthly > 0) {
      const annuityFactor = ((Math.pow(1 + rMonthly, months) - 1) / rMonthly) * (1 + rMonthly);
      extraMonthly = Math.ceil(gap / annuityFactor);
    } else {
      extraMonthly = Math.ceil(gap / months);
    }

    let low = rAnnual;
    let high = 1.0;
    let reqRate = null;
    for (let iter = 0; iter < 100; iter++) {
      const mid = (low + high) / 2.0;
      const midMonthlyRate = mid / 12.0;
      const midFvP = currentPrincipal * Math.pow(1 + mid, years);
      let midFvM = 0;
      if (midMonthlyRate > 0) {
        midFvM = monthlySurplus * ((Math.pow(1 + midMonthlyRate, months) - 1) / midMonthlyRate) * (1 + midMonthlyRate);
      } else {
        midFvM = monthlySurplus * months;
      }
      const midTotal = midFvP + midFvM + fvReserved;
      if (Math.abs(midTotal - targetAmount) < 1.0) {
        reqRate = mid;
        break;
      } else if (midTotal < targetAmount) {
        low = mid;
      } else {
        high = mid;
      }
    }
    if (reqRate === null) reqRate = high;
    const rateDiffPct = (reqRate - rAnnual) * 100.0;
    const isRateSafe = reqRate <= 0.08;

    const loosenAmount = gap;
    let delayYears = null;
    for (let extraY = 1; extraY <= 30; extraY++) {
      const curY = years + extraY;
      const curM = curY * 12;
      const curFvP = currentPrincipal * Math.pow(1 + rAnnual, curY);
      let curFvM = 0;
      if (rMonthly > 0) {
        curFvM = monthlySurplus * ((Math.pow(1 + rMonthly, curM) - 1) / rMonthly) * (1 + rMonthly);
      } else {
        curFvM = monthlySurplus * curM;
      }
      const curFvR = reservedAmount * Math.pow(1 + safeRate, curY);
      if ((curFvP + curFvM + curFvR) >= targetAmount) {
        delayYears = extraY;
        break;
      }
    }

    levers = {
      extraMonthly,
      reqRate: parseFloat((reqRate * 100.0).toFixed(2)),
      rateDiffPct: parseFloat(rateDiffPct.toFixed(2)),
      isRateSafe,
      loosenAmount: Math.round(loosenAmount),
      delayYears: delayYears || 30,
      delayedTargetYear: (targetYear + (delayYears || 30))
    };
  }

  return {
    years,
    months,
    fvPrincipal: Math.round(fvPrincipal),
    fvMonthly: Math.round(fvMonthly),
    fvReserved: Math.round(fvReserved),
    fvTotal: Math.round(fvTotal),
    diff: Math.round(diff),
    isAchieved,
    gap: Math.round(gap),
    levers
  };
}

/**
 * P1-5 多目标资金排挤与资源池分配推演模型
 */
export function calculateMultiGoalProjections(goals = [], totalInvestablePrincipal = 700000, totalMonthlySurplus = 12000, growthRate = 6.5, safeRate = 0.02) {
  // 1. 优先级排序：刚性优先，同级按到期年份由近及远
  const sorted = [...goals].map((g, idx) => ({ ...g, originalIndex: idx })).sort((a, b) => {
    if (a.priority === '刚性' && b.priority !== '刚性') return -1;
    if (a.priority !== '刚性' && b.priority === '刚性') return 1;
    return (a.targetYear || 2030) - (b.targetYear || 2030);
  });

  let remainingPrincipal = Math.max(0, totalInvestablePrincipal);
  let remainingSurplus = Math.max(0, totalMonthlySurplus);

  const goalResults = [];
  let totalAllocatedPrincipal = 0;
  let totalAllocatedSurplus = 0;

  sorted.forEach(goal => {
    const years = Math.max(1, (goal.targetYear || 2030) - 2026);
    const months = years * 12;
    const rAnnual = growthRate / 100.0;
    const rMonthly = rAnnual / 12.0;

    // 预留金
    const reserved = goal.reservedAmount || 0;
    const fvReserved = reserved * Math.pow(1 + safeRate, years);

    // 目标总需缺口
    const netTargetNeeded = Math.max(0, (goal.targetAmount || 0) - fvReserved);

    // 分配本金 (至多取所需或剩余池)
    let allocP = 0;
    if (remainingPrincipal > 0 && netTargetNeeded > 0) {
      const pNeededForTotal = netTargetNeeded / Math.pow(1 + rAnnual, years);
      allocP = Math.min(remainingPrincipal, Math.round(pNeededForTotal * 0.5)); // 50%本金贡献
    }

    // 分配月结余
    let allocS = 0;
    const fvPAlloc = allocP * Math.pow(1 + rAnnual, years);
    const remainingNeed = Math.max(0, netTargetNeeded - fvPAlloc);
    if (remainingSurplus > 0 && remainingNeed > 0) {
      const annuityFactor = rMonthly > 0 
        ? ((Math.pow(1 + rMonthly, months) - 1) / rMonthly) * (1 + rMonthly)
        : months;
      const surplusNeeded = Math.ceil(remainingNeed / annuityFactor);
      allocS = Math.min(remainingSurplus, surplusNeeded);
    }

    remainingPrincipal -= allocP;
    remainingSurplus -= allocS;
    totalAllocatedPrincipal += allocP;
    totalAllocatedSurplus += allocS;

    // 单目标推演
    const proj = calculateGoalProjection({
      currentYear: 2026,
      targetYear: goal.targetYear || 2030,
      targetAmount: goal.targetAmount || 0,
      monthlySurplus: allocS,
      growthRate,
      currentPrincipal: allocP,
      reservedAmount: reserved,
      safeRate
    });

    goalResults.push({
      ...goal,
      allocatedPrincipal: allocP,
      allocatedSurplus: allocS,
      projection: proj
    });
  });

  // 恢复原顺序
  goalResults.sort((a, b) => a.originalIndex - b.originalIndex);

  const isResourceCrowdedOut = remainingPrincipal <= 0 || remainingSurplus <= 0;
  return {
    goalResults,
    totalInvestablePrincipal,
    totalMonthlySurplus,
    totalAllocatedPrincipal,
    totalAllocatedSurplus,
    remainingPrincipal,
    remainingSurplus,
    isResourceCrowdedOut
  };
}

/**
 * 提前退休 85 岁全生命周期持久性推演
 */
export function simulateEarlyRetirement({
  currentAge = 35,
  retireAge = 50,
  targetAmount = 2000000,
  projectedCapitalAtRetire = null,
  monthlyExpense = 10000,
  dividendYield = 4.8,
  bufferInterestRate = 2.0,
  endAge = 85
}) {
  const totalYears = Math.max(1, endAge - retireAge);
  const totalMonths = totalYears * 12;
  const startCapital = projectedCapitalAtRetire && projectedCapitalAtRetire > 0 ? projectedCapitalAtRetire : targetAmount;
  
  let capital = startCapital;
  let lowestCapital = capital;
  let mostFragileMonth = 1;
  let depletionMonth = null;
  let depletionAge = null;

  const seasonality = {
    1: 0.02, 2: 0.02, 3: 0.03, 4: 0.05,
    5: 0.15, 6: 0.25, 7: 0.30, 8: 0.10,
    9: 0.03, 10: 0.02, 11: 0.01, 12: 0.02
  };

  const divRate = (dividendYield || 4.8) / 100.0;
  const intRate = (bufferInterestRate || 2.0) / 100.0;

  for (let m = 1; m <= totalMonths; m++) {
    const calMonth = ((m - 1) % 12) + 1;
    const currentSimAge = retireAge + (m - 1) / 12.0;

    const divWeight = seasonality[calMonth] || (1.0 / 12.0);
    const monthlyDiv = capital * divRate * divWeight;
    const monthlyInterest = Math.max(0, capital) * (intRate / 12.0);

    capital = capital + monthlyDiv + monthlyInterest - monthlyExpense;

    if (capital < lowestCapital) {
      lowestCapital = capital;
      mostFragileMonth = m;
    }

    if (capital <= 0 && depletionMonth === null) {
      depletionMonth = m;
      depletionAge = parseFloat(currentSimAge.toFixed(1));
    }
  }

  const isSustainable = depletionMonth === null;
  return {
    totalYears,
    totalMonths,
    isSustainable,
    finalCapital: Math.round(capital),
    depletionAge,
    depletionMonth,
    lowestCapital: Math.round(lowestCapital),
    mostFragileMonth,
    mostFragileAge: parseFloat((retireAge + (mostFragileMonth - 1) / 12.0).toFixed(1))
  };
}

/**
 * P0-3, P1-4 债务决策对照核心测算（消除静默覆盖，统一利差正负符号）
 */
export function calculateDebtDecisionMetrics(debtState = {}, growthRate = 6.5) {
  const bracketMedians = { '<3.5%': 3.0, '3.5-4.5%': 4.0, '4.5-6%': 5.25, '>6%': 7.2 };
  const bracket = debtState.debtRateBracket || '3.5-4.5%';
  const bracketMedian = bracketMedians[bracket] || 4.0;

  // 修复 P0-3：仅在明确勾选或填入正自定义利率时取自定义，否则取档位中值
  const isUsingCustom = Boolean(debtState.useCustomRate && debtState.customDebtRate > 0);
  const effectiveDebtRate = isUsingCustom ? debtState.customDebtRate : bracketMedian;
  const rateSourceLabel = isUsingCustom ? `自定义 ${effectiveDebtRate}%` : `档位中值 ${bracketMedian}%`;

  const conservativeYield = parseFloat(((growthRate || 6.5) * 0.7).toFixed(2));
  
  // 修复 P1-4：利差定义为 投资保守回报 − 贷款成本
  // 利差 > 0: 投资赚得多 (正利差)；利差 < 0: 贷款成本高 (负利差)
  const spread = parseFloat((conservativeYield - effectiveDebtRate).toFixed(2));
  const spreadAbs = Math.abs(spread).toFixed(2);
  const spreadSign = spread >= 0 ? '+' : '-';
  const spreadLabel = spread >= 0 
    ? `正利差 +${spreadAbs}% (保守投资收益可覆盖贷款利息成本)`
    : `负利差 -${spreadAbs}% (贷款利息成本高于保守投资收益)`;

  let decisionType = 'neutral';
  let decisionText = '';

  // 贷款成本高出投资 2% 以上 -> 利差 < -2%
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
  const fundX = typeof debtState.availableFundX === 'number' && debtState.availableFundX > 0 ? debtState.availableFundX : 200000;
  const rDebt = effectiveDebtRate / 100.0;
  const rInvest = conservativeYield / 100.0;

  const horizons = [3, 5, 10];
  const comparisonTable = horizons.map(years => {
    const fvRepay = fundX * Math.pow(1 + rDebt, years);
    const fvInvest = fundX * Math.pow(1 + rInvest, years);
    const diff = fvRepay - fvInvest;
    const diffPct = ((fvRepay - fvInvest) / fundX) * 100.0;

    let advantage = '持平';
    if (diff > 1) advantage = '提前还贷更优';
    else if (diff < -1) advantage = '坚持投资更优';

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

  const totalDebtBalance = (debtState.mortgageBalance || 0) + (debtState.carLoanBalance || 0) + (debtState.consumerLoanBalance || 0) + (debtState.businessLoanBalance || 0);
  const monthlyDebtPayment = debtState.monthlyDebtPayment || 0;
  const remainingYears = debtState.remainingYears || 15;

  return {
    bracket,
    bracketMedian,
    effectiveDebtRate,
    isUsingCustom,
    rateSourceLabel,
    sourceBadge: rateSourceLabel,
    growthRate,
    conservativeYield,
    spread,
    spreadSign,
    spreadLabel,
    decisionType,
    decisionText,
    hasHighInterestAlert,
    fundX,
    remainingYears,
    comparisonTable,
    totalDebtBalance,
    monthlyDebtPayment
  };
}

/**
 * P1-2 家庭保障缺口测算（取A组高流动性资产，意外险为寿险净缺口50%）
 */
export function calculateInsuranceGap(healthState = {}, insuranceState = {}, totalDebtBalance = 0) {
  const stabilityMap = INSURANCE_STABILITY_CONFIG;
  const monthlyIncome = healthState.monthlyIncome || 30000;
  const annualIncome = monthlyIncome * 12;
  const essentialMonthly = healthState.essentialMonthlyExpense || 12000;
  const future10yExpense = essentialMonthly * 120; // 10年刚需

  // P1-2: 寿险扣除的流动资产取 A 组高流动性资产 (现金活期 + 货基短债)
  const assetsBreakdown = healthState.assetsBreakdown || {};
  const highLiquidAssets = (assetsBreakdown.cashCurrent || 0) + (assetsBreakdown.cashShortDebt || 0);

  // 子女教育金独立取数
  const childEduTarget = insuranceState.childEduTarget || 500000;

  // 1. 寿险总需求与净缺口
  const lifeTarget = Math.max(0, totalDebtBalance + future10yExpense + childEduTarget - highLiquidAssets);
  const existingLife = insuranceState.existingLifeCover || 0;
  const lifeGap = Math.max(0, lifeTarget - existingLife);

  // 2. 重疾险
  const stabKey = insuranceState.stabilityTier || 'medium';
  const stabConfig = stabilityMap[stabKey] || stabilityMap.medium;
  const critTarget = stabConfig.years * annualIncome + stabConfig.medical;
  const existingCrit = insuranceState.existingCritCover || 0;
  const critGap = Math.max(0, critTarget - existingCrit);

  // 3. 意外险：P1-2 修正为寿险净缺口的 50%
  const accidentTarget = Math.round(lifeGap * 0.5);
  const existingAccident = insuranceState.existingAccidentCover || 0;
  const accidentGap = Math.max(0, accidentTarget - existingAccident);

  const hasMillionMedical = Boolean(insuranceState.hasMillionMedical);
  const hasNetGap = (lifeGap > 0) || (critGap > 0) || (accidentGap > 0) || (!hasMillionMedical);
  const isCoverageSelfReportedWeak = insuranceState.coverageTier === 'none' || insuranceState.coverageTier === 'insufficient';
  const shouldWarnAndDowngrade = isCoverageSelfReportedWeak && hasNetGap;

  return {
    highLiquidAssets,
    liquidCashDeduction: highLiquidAssets,
    childEduTarget,
    lifeTarget: Math.round(lifeTarget),
    existingLife,
    lifeGap: Math.round(lifeGap),
    lifeGapIncomeMultiple: parseFloat((lifeGap / Math.max(1, annualIncome)).toFixed(1)),
    stabConfig,
    critTarget: Math.round(critTarget),
    existingCrit,
    critGap: Math.round(critGap),
    critGapIncomeMultiple: parseFloat((critGap / Math.max(1, annualIncome)).toFixed(1)),
    accidentTarget,
    existingAccident,
    accidentGap,
    hasMillionMedical,
    shouldWarnAndDowngrade
  };
}

/**
 * 个人养老金税优测算
 */
export function calculatePensionTaxBenefit(pensionState = {}) {
  const deposited = Math.min(PENSION_ANNUAL_MAX, Math.max(0, pensionState.currentYearDeposited || 0));
  const remainingQuota = Math.max(0, PENSION_ANNUAL_MAX - deposited);
  const taxRate = pensionState.marginalTaxRate || 0.20;

  const annualTaxSavingsForegone = Math.round(remainingQuota * taxRate);
  const cumulative20ySavings = Math.round(annualTaxSavingsForegone * 20);

  return {
    hasAccount: Boolean(pensionState.hasAccount),
    deposited,
    remainingQuota,
    taxRate,
    annualTaxSavingsForegone,
    cumulative20ySavings,
    isTaxFreeTier: taxRate <= 0.001
  };
}

/**
 * P1-3 房产集中度强化与首付资金核验（双口径对比与极端下跌冲击）
 */
export function calculateRealEstateRisk(propertyState = {}, healthState = {}, debtState = {}) {
  const propertyVal = propertyState.totalEstimatedValue || 2800000;
  const mortgage = debtState.mortgageBalance || 800000;
  const totalDebt = (debtState.mortgageBalance || 0) + (debtState.carLoanBalance || 0) + (debtState.consumerLoanBalance || 0) + (debtState.businessLoanBalance || 0);

  const breakdown = healthState.assetsBreakdown || {};
  const liquidFinancial = (breakdown.cashCurrent || 0) + (breakdown.cashShortDebt || 0) + (breakdown.equityAssets || 0) + (breakdown.goldAssets || 0) + (breakdown.bondAssets || 0) + (breakdown.otherAssets || 0);
  const pensionCashValue = breakdown.pensionCashValue || 0;

  const familyTotalAssets = liquidFinancial + propertyVal + pensionCashValue;
  const familyTotalNetWorth = Math.max(1, familyTotalAssets - totalDebt);

  const propertyNet = Math.max(0, propertyVal - mortgage);
  const ratio = parseFloat(((propertyNet / familyTotalNetWorth) * 100.0).toFixed(1));

  let tier = 'green';
  let tierLabel = '安全适中 (<60%)';
  if (ratio > PROPERTY_THRESHOLDS.yellowMax * 100) {
    tier = 'red';
    tierLabel = '高危过重 (>75%)';
  } else if (ratio >= PROPERTY_THRESHOLDS.greenMax * 100) {
    tier = 'yellow';
    tierLabel = '偏高关注 (60-75%)';
  }

  // 首付校验
  const hasHousePlan = Boolean(healthState.hasHousePlan);
  const expectedDownPayment = healthState.expectedDownPayment || 600000;
  const readyFunds = (breakdown.cashCurrent || 0) + (breakdown.cashShortDebt || 0);
  const downPaymentGap = Math.max(0, expectedDownPayment - readyFunds);
  const isDownPaymentShort = hasHousePlan && downPaymentGap > 0;

  // P1-3 房产下跌 20% 冲击
  const stressDropPct = propertyState.stressDropPct || 20;
  const propertyLoss = Math.round(propertyVal * (stressDropPct / 100.0));
  const stressTotalAssets = Math.max(1, familyTotalAssets - propertyLoss);
  const stressNetWorth = Math.max(0, familyTotalNetWorth - propertyLoss);
  const stressDebtToAssetRatio = parseFloat(((totalDebt / stressTotalAssets) * 100.0).toFixed(1));
  const normalDebtToAssetRatio = parseFloat(((totalDebt / familyTotalAssets) * 100.0).toFixed(1));

  // 双口径对比
  // 口径 A: 含房产
  const perspectiveA = {
    totalAssets: familyTotalAssets,
    totalDebt,
    netWorth: familyTotalNetWorth,
    debtRatio: normalDebtToAssetRatio
  };
  // 口径 B: 纯金融（不含房产与房贷）
  const pureFinancialAssets = liquidFinancial + pensionCashValue;
  const nonMortgageDebt = Math.max(0, totalDebt - mortgage);
  const pureFinancialNetWorth = pureFinancialAssets - nonMortgageDebt;
  const pureFinancialDebtRatio = pureFinancialAssets > 0 ? parseFloat(((nonMortgageDebt / pureFinancialAssets) * 100.0).toFixed(1)) : 0;

  const perspectiveB = {
    pureFinancialAssets,
    nonMortgageDebt,
    pureFinancialNetWorth,
    pureFinancialDebtRatio
  };

  return {
    propertyVal,
    mortgage,
    propertyNet,
    familyTotalAssets,
    familyTotalNetWorth,
    ratio,
    tier,
    tierLabel,
    hasHousePlan,
    expectedDownPayment,
    readyFunds,
    downPaymentGap,
    isDownPaymentShort,
    perspectiveA,
    perspectiveB,
    stressDropPct,
    propertyLoss,
    stressTotalAssets,
    stressNetWorth,
    normalDebtToAssetRatio,
    stressDebtToAssetRatio
  };
}

/**
 * P1-1 流动性硬隔离校验（A组资产与B组支出彻底解耦）
 */
export function checkLiquiditySegregation(healthState = {}, boardPrincipalTenThousand = 80) {
  const breakdown = healthState.assetsBreakdown || {};
  const liquidFinancialAssets = (breakdown.cashCurrent || 0) + (breakdown.cashShortDebt || 0) + (breakdown.equityAssets || 0) + (breakdown.goldAssets || 0) + (breakdown.bondAssets || 0) + (breakdown.otherAssets || 0);

  const expenses = healthState.expectedExpenses || {};
  const expense1y = expenses.expense1y || 100000;
  const expense1To3y = expenses.expense1To3y || 150000;

  // 可投资上限 = 流动金融资产 - 12m*100% - 1-3y*50%
  const investableCeiling = Math.max(0, liquidFinancialAssets - (expense1y * 1.0) - (expense1To3y * LIQUIDITY_DISCOUNT_FACTOR));
  const boardPrincipalYuan = boardPrincipalTenThousand * 10000;
  const isViolated = boardPrincipalYuan > investableCeiling;
  const excessAmount = Math.max(0, boardPrincipalYuan - investableCeiling);

  const shortTermExpenses = expense1y + expense1To3y;
  const coverageRatio = shortTermExpenses > 0 ? parseFloat((liquidFinancialAssets / shortTermExpenses).toFixed(2)) : 99.0;
  const isCoverageInsufficient = coverageRatio < LIQUIDITY_SAFE_COVERAGE_RATIO;

  return {
    liquidFinancialAssets,
    expense1y,
    expense1To3y,
    bucket1y: expense1y,
    bucket1To3y: expense1To3y,
    discountFactor: LIQUIDITY_DISCOUNT_FACTOR,
    investableCeiling: Math.round(investableCeiling),
    boardPrincipalYuan,
    isViolated,
    excessAmount: Math.round(excessAmount),
    warningText: isViolated ? `当前本金侵占未来确定性刚需，超限 ¥${Math.round(excessAmount).toLocaleString()} 元，建议调减投资本金或压缩短期预算！` : '可用投资本金处于安全可控限额内。',
    distinctionNote: '流动性硬隔离（资产体检）：防范本金侵入1-3年确定性大额刚需；现金缓冲池（看板）：防范月度必要生活开支与分红淡旺季错配。两者定位严格互补。',
    coverageRatio,
    isCoverageInsufficient
  };
}

/**
 * 三重集中度检查
 */
export function checkTripleConcentration(assets = {}) {
  const assetList = Object.entries(assets).map(([code, item]) => ({
    code,
    name: item.name,
    weight: item.weight || 0,
    market: item.market || 'A股',
    category: item.category || 'Equity',
    style: item.style || '其他'
  }));

  // 1. 标的集中度
  const sorted = [...assetList].sort((a, b) => b.weight - a.weight);
  const maxSingle = sorted[0] || { name: '无', weight: 0 };
  const top3Weight = parseFloat(sorted.slice(0, 3).reduce((acc, cur) => acc + cur.weight, 0).toFixed(1));

  const isSingleWarn = maxSingle.weight > CONCENTRATION_LIMITS.singleAssetYellow;
  const isTop3Danger = top3Weight > CONCENTRATION_LIMITS.top3AssetsRed;

  let targetStatus = 'green';
  let targetAdvice = '标的分布分散均匀，单一资产黑天鹅冲击可控。';
  if (isTop3Danger) {
    targetStatus = 'red';
    targetAdvice = `前三大标的合计权重达到 ${top3Weight}% (红灯>70%)，需防范极端踩踏。`;
  } else if (isSingleWarn) {
    targetStatus = 'yellow';
    targetAdvice = `单一标的【${maxSingle.name}】达 ${maxSingle.weight.toFixed(1)}% (黄灯>40%)，单资产冲击显著。`;
  }

  // 2. 市场集中度
  const marketSums = {};
  assetList.forEach(a => {
    marketSums[a.market] = (marketSums[a.market] || 0) + a.weight;
  });
  let maxMarket = { market: 'A股', weight: 0 };
  Object.entries(marketSums).forEach(([m, w]) => {
    if (w > maxMarket.weight) maxMarket = { market: m, weight: parseFloat(w.toFixed(1)) };
  });

  const isMarketAlert = maxMarket.weight > CONCENTRATION_LIMITS.marketCurrencyAlert;
  let marketStatus = isMarketAlert ? 'yellow' : 'green';
  let marketAdvice = isMarketAlert 
    ? `【${maxMarket.market}】资产占比高达 ${maxMarket.weight}% (>60%)，建议适度跨市场分散。`
    : '多市场均衡分布，宏观主权风险分散良好。';

  // 3. 策略风格集中度 (红利低波)
  let dividendStyleWeight = 0;
  assetList.forEach(a => {
    if (a.style === '红利低波') dividendStyleWeight += a.weight;
  });
  dividendStyleWeight = parseFloat(dividendStyleWeight.toFixed(1));

  const isStyleAlert = dividendStyleWeight > CONCENTRATION_LIMITS.dividendStyleClusterAlert;
  let styleStatus = isStyleAlert ? 'yellow' : 'green';
  let styleAdvice = isStyleAlert
    ? `红利低波类标的权重达 ${dividendStyleWeight}% (>50%)，需注意银行/煤炭行业周期共振风险。`
    : '风格保持多元平衡。';

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
 * P0-4 行为约束引擎（严格按 category === 'Equity' 统计实际权益权重）
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

  // P0-4 严格按 category === 'Equity' 判定实际权益
  let actualEquityWeight = 0;
  Object.values(assets).forEach(a => {
    if (a.category === 'Equity') {
      actualEquityWeight += (a.weight || 0);
    }
  });
  actualEquityWeight = parseFloat(actualEquityWeight.toFixed(1));

  const isExceeded = actualEquityWeight > finalCeiling;
  const excessWeight = parseFloat(Math.max(0, actualEquityWeight - finalCeiling).toFixed(1));
  const implicitDrawdown = parseFloat((finalCeiling * BEHAVIOR_RULES.extremeEquityDrawdown).toFixed(1));

  const breakdownList = [
    { label: `自评回撤档位 (${bracket}) 基础权益上限`, delta: `+${baseCeiling}%` }
  ];
  if (panicDeduction > 0) breakdownList.push({ label: '市场大跌第一反应 (恐慌卖出/观望)', delta: `-${panicDeduction}%` });
  if (cashflowDeduction > 0) breakdownList.push({ label: '日常现金流高度依赖投资收益', delta: `-${cashflowDeduction}%` });
  if (industryDeduction > 0) breakdownList.push({ label: '行业波动大且失业恢复期预期>6个月', delta: `-${industryDeduction}%` });
  if (rawCeiling < BEHAVIOR_RULES.floorProtection) breakdownList.push({ label: `触发工具安全保护底线 (${BEHAVIOR_RULES.floorProtection}%)`, delta: '兜底提升' });

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
 * P2-1 估值温度计（修复 20% 边界归入低估而非深度低估）
 */
export function calculateThermometerSignal(percentile = 50) {
  const val = Math.min(100, Math.max(0, percentile));
  let code = 'neutral';
  
  // 修复边界：< 20 为深度低估；20 <= val < 40 为低估
  if (val < 20) code = 'deep_low';
  else if (val < 40) code = 'low';
  else if (val < 60) code = 'neutral';
  else if (val < 80) code = 'warm';
  else code = 'overheat';

  const tier = THERMOMETER_TIERS.find(t => t.code === code) || THERMOMETER_TIERS[2];

  // 动态定投调节因子
  let dcaFactor = 1.0;
  if (code === 'deep_low') dcaFactor = 1.5;
  else if (code === 'low') dcaFactor = 1.2;
  else if (code === 'neutral') dcaFactor = 1.0;
  else if (code === 'warm') dcaFactor = 0.5;
  else if (code === 'overheat') dcaFactor = 0.0;

  return {
    percentile: val,
    code,
    tier,
    dcaFactor,
    dcaMultiplier: dcaFactor,
    isOverheated: code === 'overheat',
    isDeepLow: code === 'deep_low',
    actionAdvice: tier.action,
    rebalanceAdvice: code === 'overheat' 
      ? '过热预警：建议启动卖出侧纪律，分批止盈并再平衡至防守桶'
      : (code === 'deep_low' ? '黄金买点：定投力度加码，摊薄中长期持仓成本' : '保持常规纪律操作')
  };
}

/**
 * P2-2 增量资金再平衡分配算法
 */
export function calculateIncrementalRebalance(assets = {}, userHoldings = {}, incrementalCapital = 50000) {
  const safeHoldings = userHoldings || {};
  // 计算当前持仓市值
  let totalCurrentValYuan = 0;
  const holdingList = Object.entries(assets || {}).map(([code, asset]) => {
    const valWan = Number(safeHoldings[code] ?? 0);
    const valYuan = valWan * 10000;
    totalCurrentValYuan += valYuan;
    return {
      code,
      name: asset.name,
      targetWeight: asset.weight || 0,
      targetPct: asset.weight || 0,
      valYuan
    };
  });

  const totalAfterCapital = totalCurrentValYuan + incrementalCapital;

  // 识别低配标的
  const rebalanceItems = holdingList.map(item => {
    const currentWeight = totalCurrentValYuan > 0 ? (item.valYuan / totalCurrentValYuan) * 100.0 : item.targetWeight;
    const weightDiff = currentWeight - item.targetWeight; // 实际 - 目标
    const idealValAfter = totalAfterCapital * (item.targetWeight / 100.0);
    const neededGap = Math.max(0, idealValAfter - item.valYuan); // 补齐目标还需资金

    return {
      ...item,
      currentWeight: parseFloat(currentWeight.toFixed(1)),
      currentPct: parseFloat(currentWeight.toFixed(1)),
      weightDiff: parseFloat(weightDiff.toFixed(1)),
      diffPct: parseFloat(weightDiff.toFixed(1)),
      status: weightDiff > 2.0 ? 'overweight' : (weightDiff < -2.0 ? 'underweight' : 'balanced'),
      neededGap
    };
  });

  const totalNeededGaps = rebalanceItems.reduce((acc, cur) => acc + cur.neededGap, 0);

  // 增量资金全额分配至低配标的
  const allocation = rebalanceItems.map(item => {
    let allocatedYuan = 0;
    if (totalNeededGaps > 0 && item.neededGap > 0) {
      allocatedYuan = Math.round((item.neededGap / totalNeededGaps) * incrementalCapital);
    }
    return {
      ...item,
      allocatedYuan,
      allocatedCash: allocatedYuan
    };
  });

  return {
    totalCurrentValYuan,
    totalAfterCapital,
    incrementalCapital,
    allocation,
    allocations: allocation
  };
}

/**
 * P0-1, P0-2 复合情景压力测试推演引擎（失业期收入减损 + 真实逐月回撤）
 */
export function runCompoundStressTest(boardState = {}, stressScenario = {}, healthState = {}, monthsRange = 36) {
  const { principal, bufferSeed, targetMonthly, moneyMarketRate, assets = {} } = boardState;
  const investPrincipalYuan = Math.max(0, principal - bufferSeed) * 10000;
  const mmRate = (moneyMarketRate || 2.0) / 100.0;

  const unemploymentMonths = stressScenario.unemploymentMonths || 0;
  const replacementRate = typeof stressScenario.unemploymentReplacementRate === 'number' 
    ? stressScenario.unemploymentReplacementRate 
    : (healthState.unemploymentReplacementRate !== undefined ? healthState.unemploymentReplacementRate : 0.3);

  const monthlyIncome = healthState.monthlyIncome || 30000;
  const essentialExpense = healthState.essentialMonthlyExpense || 12000;
  // P0-1 失业期每月收入减损造成的额外现金流出
  const unemploymentLossPerMonth = Math.max(0, essentialExpense - (monthlyIncome * replacementRate));

  const dividendDropRate = stressScenario.dividendDropRate || 0;
  const delayMonths = stressScenario.delayMonths || 0;
  const medicalExpense = stressScenario.medicalExpense || 0;
  const medicalMonth = stressScenario.medicalMonth || 6;
  const inflationRate = stressScenario.inflationRate || 0;

  // P0-2 历史回放时序回撤与分红系数
  const monthlyDrawdowns = stressScenario.monthlyDrawdown || null;
  const replayDividendFactor = stressScenario.dividendFactor !== undefined ? stressScenario.dividendFactor : 1.0;
  const defaultEquityDrawdown = stressScenario.equityDrawdownRate || 0.20;

  let currentBuffer = bufferSeed * 10000;
  const timeline = [];
  let minBuffer = currentBuffer;
  let exhaustionMonth = null;
  let maxDeficit = 0;
  let worstDeficitMonth = 1;

  for (let t = 1; t <= monthsRange; t++) {
    const calendarMonth = ((t - 1) % 12) + 1;
    let baseMonthlyWithdraw = (targetMonthly || 1.2) * 10000;
    if (inflationRate > 0) {
      baseMonthlyWithdraw = baseMonthlyWithdraw * Math.pow(1 + inflationRate / 12.0, t);
    }

    // P0-1 失业期收入减损生效
    const isUnemployed = t <= unemploymentMonths;
    const unemploymentLoss = isUnemployed ? unemploymentLossPerMonth : 0;

    let extraMedical = 0;
    if (medicalExpense > 0 && t === medicalMonth) {
      extraMedical = medicalExpense;
    }

    const totalOutflow = baseMonthlyWithdraw + unemploymentLoss + extraMedical;

    // 分红到账
    let monthDividend = 0;
    const effectiveCalMonth = delayMonths > 0 ? ((((calendarMonth - 1 - delayMonths) % 12) + 12) % 12) + 1 : calendarMonth;

    Object.values(assets).forEach(asset => {
      const distRatio = (asset.months && asset.months[effectiveCalMonth]) || 0;
      if (distRatio > 0) {
        const assetVal = investPrincipalYuan * ((asset.weight || 0) / 100.0);
        const baseDiv = assetVal * ((asset.yield || 0) / 100.0) * distRatio;
        monthDividend += baseDiv * (1 - dividendDropRate) * replayDividendFactor;
      }
    });

    const monthInterest = Math.max(0, currentBuffer) * (mmRate / 12.0);
    const nextBuffer = currentBuffer + monthDividend + monthInterest - totalOutflow;

    if (currentBuffer < minBuffer) minBuffer = currentBuffer;
    if (nextBuffer < 0 && exhaustionMonth === null) exhaustionMonth = t;
    if (nextBuffer < 0 && Math.abs(nextBuffer) > maxDeficit) {
      maxDeficit = Math.abs(nextBuffer);
      worstDeficitMonth = t;
    }

    // P0-2 当月时序回撤
    let currentDrawdown = defaultEquityDrawdown;
    if (Array.isArray(monthlyDrawdowns) && monthlyDrawdowns.length > 0) {
      const idx = Math.min(t - 1, monthlyDrawdowns.length - 1);
      currentDrawdown = Math.abs(monthlyDrawdowns[idx]);
    }

    timeline.push({
      month: t,
      calendarMonth,
      isUnemployed,
      unemploymentLoss: Math.round(unemploymentLoss),
      startBuffer: Math.round(currentBuffer),
      dividend: Math.round(monthDividend),
      interest: parseFloat(monthInterest.toFixed(1)),
      withdraw: Math.round(totalOutflow),
      medicalExpense: extraMedical,
      endBuffer: Math.round(nextBuffer),
      drawdownRate: currentDrawdown
    });

    currentBuffer = nextBuffer;
  }

  // P0-2 变现资产规模按最深亏空时点的回撤折算
  const worstMonthDrawdown = (timeline[worstDeficitMonth - 1] && timeline[worstDeficitMonth - 1].drawdownRate) || defaultEquityDrawdown;
  const discountMultiplier = Math.max(0.1, 1 - worstMonthDrawdown);
  const minAssetToSell = exhaustionMonth ? Math.round(maxDeficit / discountMultiplier) : 0;

  const monthlySurplusYuan = healthState.monthlySurplus || 12000;
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
    unemploymentLossPerMonth: Math.round(unemploymentLossPerMonth),
    unemploymentLossTotal: Math.round(unemploymentLossPerMonth * unemploymentMonths),
    unemploymentMonths,
    worstMonthDrawdown
  };
}

/**
 * P1-6, P1-7 评分体系重构（7因子脆弱性归因 + 4客观行为进攻性评分）
 */
export function calculateExplainableScores(state = {}) {
  const { board = {}, health = {}, debt = {}, insurance = {}, behavior = {} } = state;
  const boardMetrics = calculateBoardMetrics(board);
  const bufferSim = calculateBufferSimulation(board);
  const debtMetrics = calculateDebtDecisionMetrics(debt, board.growthRate);
  const insGap = calculateInsuranceGap(health, insurance, debtMetrics.totalDebtBalance);
  const liqCheck = checkLiquiditySegregation(health, board.principal);
  const behCheck = calculateBehavioralEquityCeiling(behavior, board.assets);

  // ==========================================
  // 一、脆弱性评分 (0 - 100 分，越低越稳健，满分100代表极度脆弱)
  // 7 大明确子因子
  // ==========================================
  // 1. 高息债务与债务总杠杆 (0-20分)
  let fDebt = 0;
  if (debtMetrics.hasHighInterestAlert) fDebt = 20;
  else if (debtMetrics.totalDebtBalance > 1500000) fDebt = 14;
  else if (debtMetrics.totalDebtBalance > 0) fDebt = 7;

  // 2. 月供占月收入比 (0-15分)
  const monthlyIncome = healthStateIncome(health);
  const repayRatio = monthlyIncome > 0 ? ((debtMetrics.monthlyDebtPayment || 0) / monthlyIncome) : 0;
  let fRepay = 0;
  if (repayRatio > 0.5) fRepay = 15;
  else if (repayRatio > 0.35) fRepay = 9;
  else if (repayRatio > 0) fRepay = 4;

  // 3. 流动性硬隔离违规与备用金覆盖 (0-20分)
  let fLiq = 0;
  if (liqCheck.isViolated) fLiq = 20;
  else if (liqCheck.isCoverageInsufficient) fLiq = 12;
  else fLiq = 3;

  // 4. 收入结构单一性 (0-15分)
  const incSource = health.incomeSourceCount || 'single';
  let fInc = 0;
  if (incSource === 'single') fInc = 15;
  else if (incSource === 'dual') fInc = 8;
  else fInc = 2; // multiple

  // 5. 预期失业恢复期 (0-10分)
  const recMonths = health.unemploymentRecoveryMonths || 6;
  let fRec = 0;
  if (recMonths > 6) fRec = 10;
  else if (recMonths >= 3) fRec = 5;
  else fRec = 0;

  // 6. 保障缺口敞口与百万医疗兜底 (0-10分)
  let fIns = 0;
  if (insGap.shouldWarnAndDowngrade) fIns = 10;
  else if (insGap.lifeGap > 0 || insGap.critGap > 0 || !insGap.hasMillionMedical) fIns = 6;

  // 7. 缓冲池淡旺季平滑最低水位 (0-10分)
  let fBuf = 0;
  if (!bufferSim.isBufferSafe) fBuf = 10;
  else if (bufferSim.minBuffer < 30000) fBuf = 5;

  const totalVulnerability = fDebt + fRepay + fLiq + fInc + fRec + fIns + fBuf;

  const vulnFactors = [
    { name: '高息与综合债务杠杆', score: fDebt, max: 20, desc: debtMetrics.hasHighInterestAlert ? '存在高息债务或利率>6%' : `总负债 ¥${debtMetrics.totalDebtBalance.toLocaleString()}元` },
    { name: '还贷月供收入比', score: fRepay, max: 15, desc: `月供占比 ${(repayRatio * 100).toFixed(1)}%` },
    { name: '流动性硬隔离与应急覆盖', score: fLiq, max: 20, desc: liqCheck.isViolated ? `超限违规 ¥${liqCheck.excessAmount.toLocaleString()}元` : `覆盖倍数 ${liqCheck.coverageRatio}x` },
    { name: '家庭收入结构多元性', score: fInc, max: 15, desc: incSource === 'single' ? '单薪依赖度高' : (incSource === 'dual' ? '双薪家庭' : '多元收入来源') },
    { name: '失业恢复期预期', score: fRec, max: 10, desc: `恢复期预期 ${recMonths} 个月` },
    { name: '家庭人身保障缺口与医疗兜底', score: fIns, max: 10, desc: insGap.shouldWarnAndDowngrade ? '自评不足且有缺口' : (insGap.hasMillionMedical ? '保障齐备' : '缺百万医疗') },
    { name: '缓冲池淡旺季平滑', score: fBuf, max: 10, desc: !bufferSim.isBufferSafe ? '出现亏空断流' : `最低水位 ¥${bufferSim.minBuffer.toLocaleString()}` }
  ];

  vulnFactors.sort((a, b) => (b.score / b.max) - (a.score / a.max));
  const worstVulnFactor = vulnFactors[0];

  // ==========================================
  // 二、理财进攻性评分 (0 - 100 分，纯客观行为持仓重构)
  // 4 大客观子因子
  // ==========================================
  // 1. 严格权益持仓占比 (0-35分)
  const equityWeight = behCheck.actualEquityWeight;
  const fEq = Math.min(35, Math.round((equityWeight / 100.0) * 35));

  // 2. 高波动与海外市场暴露 (0-25分)
  let highVolWeight = 0;
  Object.values(board.assets || {}).forEach(a => {
    if (a.market === '港股' || a.market === '美股' || a.style === '成长' || a.style === '科创') {
      highVolWeight += (a.weight || 0);
    }
  });
  const fVol = Math.min(25, Math.round((highVolWeight / 100.0) * 25));

  // 3. 杠杆水平与高息博取 (0-20分)
  let fLev = 0;
  if (debtMetrics.hasHighInterestAlert) fLev = 20;
  else if (repayRatio > 0.4) fLev = 14;
  else if (debtMetrics.totalDebtBalance > 0) fLev = 8;

  // 4. 超越行为约束上限博取度 (0-20分)
  const fExceed = behCheck.isExceeded ? Math.min(20, Math.round(behCheck.excessWeight * 1.5)) : 0;

  const totalAggressiveness = Math.min(100, fEq + fVol + fLev + fExceed);

  const aggFactors = [
    { name: '严格口径权益持仓权重', score: fEq, max: 35, desc: `权益配置比例 ${equityWeight}%` },
    { name: '高波动与海外市场暴露', score: fVol, max: 25, desc: `高波动/海外占比 ${highVolWeight.toFixed(1)}%` },
    { name: '家庭债务杠杆博取度', score: fLev, max: 20, desc: `月供占比 ${(repayRatio * 100).toFixed(1)}%` },
    { name: '突破行为约束上限超配度', score: fExceed, max: 20, desc: behCheck.isExceeded ? `超配上限 ${behCheck.excessWeight}%` : '未超越约束' }
  ];

  return {
    totalVulnerability,
    vulnerabilityLevel: totalVulnerability > 60 ? '高危脆弱' : (totalVulnerability > 35 ? '中度脆弱' : '稳健安全'),
    vulnFactors,
    worstVulnConclusion: `本期【${worstVulnFactor.name}】得分为 ${worstVulnFactor.score}分 (满分${worstVulnFactor.max}分)，是推高家庭财务脆弱性的首要短板。`,
    totalAggressiveness,
    aggressivenessLevel: totalAggressiveness > 70 ? '激进进攻' : (totalAggressiveness > 40 ? '平衡进取' : '谨慎保守'),
    aggFactors
  };
}

function healthStateIncome(health) {
  return health.monthlyIncome || 30000;
}

/**
 * 统一风险仪表盘 (汇聚 6 大红黄绿灯风险源)
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
      advice: liqCheck.isViolated ? '请调减本金，隔离短期确定资金' : '保持短期资金与投资资金硬隔离'
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
        ? `前三标的占比达 ${concentration.top3Weight}%`
        : (concentration.styleStatus === 'yellow' ? `红利低波风格达 ${concentration.dividendStyleWeight}%` : '资产分散度良好'),
      advice: concentration.targetAdvice
    },
    {
      id: 'behavior_constraint',
      name: '行为风险约束',
      targetTab: 'board',
      targetAnchor: 'behavior-constraint-card',
      level: behCheck.isExceeded ? 'red' : 'green',
      desc: behCheck.isExceeded 
        ? `实际权益 ${behCheck.actualEquityWeight}% 超过行为上限 (${behCheck.finalCeiling}%)`
        : `权益仓位符合心理耐受 (上限 ${behCheck.finalCeiling}%)`,
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
