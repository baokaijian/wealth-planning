// src/constants.js

// 默认资产配置池（扩充板块、币种与风格分类供集中度检查）
export const DEFAULT_ASSETS = {
  '512890': {
    name: '中证红利低波 ETF',
    type: 'ETF',
    weight: 20.0,
    yield: 4.5,
    months: { 7: 0.5, 12: 0.5 },
    market: 'A股',
    category: 'Equity',
    style: '红利低波'
  },
  '515450': {
    name: '标普大盘红利低波 ETF',
    type: 'ETF',
    weight: 15.0,
    yield: 4.2,
    months: { 7: 1.0 },
    market: 'A股',
    category: 'Equity',
    style: '红利低波'
  },
  '513530': {
    name: '恒生红利低波 ETF',
    type: 'ETF',
    weight: 15.0,
    yield: 4.8,
    months: { 7: 0.5, 12: 0.5 },
    market: '港股',
    category: 'Equity',
    style: '红利低波'
  },
  '600941': {
    name: '中国移动 (个股)',
    type: 'Stock',
    weight: 10.0,
    yield: 6.0,
    months: { 6: 0.6, 9: 0.4 },
    market: 'A股',
    category: 'Equity',
    style: '红利低波'
  },
  '600900': {
    name: '长江电力 (个股)',
    type: 'Stock',
    weight: 10.0,
    yield: 3.71,
    months: { 7: 1.0 },
    market: 'A股',
    category: 'Equity',
    style: '红利低波'
  },
  '601398': {
    name: '工商银行 (个股)',
    type: 'Stock',
    weight: 10.0,
    yield: 5.5,
    months: { 7: 0.7, 12: 0.3 },
    market: 'A股',
    category: 'Equity',
    style: '红利低波'
  },
  '601088': {
    name: '中国神华 (个股)',
    type: 'Stock',
    weight: 10.0,
    yield: 4.77,
    months: { 7: 1.0 },
    market: 'A股',
    category: 'Equity',
    style: '红利低波'
  },
  '601668': {
    name: '中国建筑 (个股)',
    type: 'Stock',
    weight: 10.0,
    yield: 5.52,
    months: { 6: 1.0 },
    market: 'A股',
    category: 'Equity',
    style: '红利低波'
  }
};

// 目标类型与优先级
export const GOAL_TYPES = [
  '子女教育金',
  '养老储备',
  '买房首付',
  '提前退休',
  '自定义'
];

export const GOAL_PRIORITIES = [
  '刚性',
  '弹性'
];

// 贷款利率档位与中值映射
export const DEBT_RATE_BRACKETS = {
  '<3.5%': { label: '<3.5% (公积金/超低息)', median: 3.0 },
  '3.5-4.5%': { label: '3.5-4.5% (主流商贷/优质消费贷)', median: 4.0 },
  '4.5-6%': { label: '4.5-6% (早期商贷/一般消费贷)', median: 5.25 },
  '>6%': { label: '>6% (高息网贷/信用卡分期)', median: 7.2 }
};

// 1. 保障缺口测算行业稳定性联动配置
export const INSURANCE_STABILITY_CONFIG = {
  high: { years: 3, medical: 300000, label: '高稳定 (体制内/大型垄断国企)' },
  medium: { years: 4, medical: 400000, label: '中等稳定 (成熟实业/常规外企)' },
  low: { years: 5, medical: 500000, label: '波动大 (互联网/金融/初创/销售佣金)' }
};

// 保障自评档位
export const INSURANCE_COVERAGE_TIERS = [
  { id: 'none', label: '极低/空白 (仅基本医保或无商业险)', warning: true },
  { id: 'insufficient', label: '基础不足 (仅少量单位团险或低保额意外)', warning: true },
  { id: 'moderate', label: '基本齐备 (常规寿险/重疾但保额一般)', warning: false },
  { id: 'complete', label: '充足全面 (高额寿险+重疾+百万医疗兜底)', warning: false }
];

// 4. 个人养老金常数
export const PENSION_ANNUAL_MAX = 12000;
export const PENSION_TAX_BRACKETS = [
  { rate: 0.0, label: '不达起征点 (0%)' },
  { rate: 0.03, label: '3% (年应税所得 ≤ 3.6万)' },
  { rate: 0.10, label: '10% (3.6万 - 14.4万)' },
  { rate: 0.20, label: '20% (14.4万 - 30万)' },
  { rate: 0.25, label: '25% (30万 - 42万)' },
  { rate: 0.30, label: '30% (42万 - 66万)' },
  { rate: 0.35, label: '35% (66万 - 96万)' },
  { rate: 0.45, label: '45% (年应税所得 > 96万)' }
];

// 5. 房产集中度预警阈值
export const PROPERTY_THRESHOLDS = {
  greenMax: 0.60,
  yellowMax: 0.75,
  defaultStressDropPct: 20
};

// 6. 复合压力测试预设情景
export const STRESS_PRESETS = {
  standard: {
    id: 'standard',
    name: '标准复合情景',
    description: '失业 6 个月 + 组合分红降 30% + 权益市值同步回撤 20%',
    unemploymentMonths: 6,
    dividendDropRate: 0.30,
    equityDrawdownRate: 0.20,
    medicalExpense: 0,
    medicalMonth: 0,
    delayMonths: 0,
    inflationRate: 0.0
  },
  severe: {
    id: 'severe',
    name: '严重复合情景',
    description: '失业 12 个月 + 组合分红降 50% + 权益市值回撤 35% + 第 6 个月突发一次性医疗 20 万元',
    unemploymentMonths: 12,
    dividendDropRate: 0.50,
    equityDrawdownRate: 0.35,
    medicalExpense: 200000,
    medicalMonth: 6,
    delayMonths: 0,
    inflationRate: 0.0
  },
  stagflation: {
    id: 'stagflation',
    name: '滞胀情景',
    description: '年通胀 5% (刚性生活支出逐月递增) + 分红延迟 4 个月到账 + 分红永久下降 20%',
    unemploymentMonths: 0,
    dividendDropRate: 0.20,
    equityDrawdownRate: 0.15,
    medicalExpense: 0,
    medicalMonth: 0,
    delayMonths: 4,
    inflationRate: 0.05
  }
};

// 6. 内置历史回放模板 (离线静态 12 个月回撤路径与分红系数)
export const HISTORICAL_REPLAYS = {
  replay_2018: {
    id: 'replay_2018',
    name: '2018 式阴跌回放',
    description: '宏观去杠杆与外部冲击，12 个月逐月阴跌累计回撤 25%，分红保持平稳发放。',
    monthlyDrawdown: [-0.02, -0.04, -0.07, -0.09, -0.12, -0.15, -0.18, -0.20, -0.22, -0.23, -0.24, -0.25],
    dividendFactor: 1.0,
    unemploymentMonths: 0
  },
  replay_2022: {
    id: 'replay_2022',
    name: '2022 式股债双杀回放',
    description: '全球加息周期与流动性收紧，权益回撤 20%，债券资产阶段回调 3%，分红下调 10%。',
    monthlyDrawdown: [-0.05, -0.08, -0.12, -0.16, -0.18, -0.20, -0.19, -0.18, -0.20, -0.20, -0.18, -0.18],
    dividendFactor: 0.90,
    unemploymentMonths: 0
  },
  replay_2015: {
    id: 'replay_2015',
    name: '2015 式急跌回放',
    description: '杠杆资金踩踏出清，前 3 个月急速暴跌 40%，随后低位宽幅剧烈震荡。',
    monthlyDrawdown: [-0.15, -0.32, -0.40, -0.38, -0.39, -0.37, -0.38, -0.36, -0.36, -0.35, -0.36, -0.35],
    dividendFactor: 0.95,
    unemploymentMonths: 0
  }
};

// 7. 行为约束引擎配置
export const BEHAVIOR_DRAWDOWN_MAP = {
  '<5%': 20,
  '5-10%': 35,
  '10-20%': 55,
  '20-30%': 70,
  '>30%': 85
};

export const BEHAVIOR_RULES = {
  panicReactionDeduction: {
    'panic_sell': 15, // 恐慌卖出 -15%
    'pause_watch': 5, // 暂停观望 -5%
    'buy_more': 0     // 逆势加仓 0%
  },
  cashflowRelianceDeduction: 10,   // 生活费高度依赖投资收益 -10%
  industryVolatileDeduction: 10,  // 行业波动大且失业恢复>6个月 -10%
  floorProtection: 15,            // 工具安全保护下限 15%
  extremeEquityDrawdown: 0.40     // 历史极端权益回撤估算 40%
};

// 8. 估值温度计五档买卖纪律
export const THERMOMETER_TIERS = [
  { min: 0, max: 20, code: 'deep_low', label: '深度低估', color: '#10B981', action: '定投倍数放大至 1.5-2.0x；若缓冲池储备超额，可将盈余资金一次性转入' },
  { min: 20, max: 40, code: 'low', label: '低估', color: '#34D399', action: '按 1.2x 步长积极定投建仓，持续累积低成本份额' },
  { min: 40, max: 60, code: 'neutral', label: '中性平衡', color: '#38BDF8', action: '估值处于合理中枢，保持既定配置目标权重，常规基准定投' },
  { min: 60, max: 80, code: 'warm', label: '估值偏热', color: '#FBBF24', action: '停止增量资金加仓，将新增可结余资金导向现金缓冲池或债券防守桶' },
  { min: 80, max: 100, code: 'overheat', label: '极度过热', color: '#F87171', action: '启动卖出侧纪律：建议按月度 3 次分批将成长类持仓再平衡回目标权重' }
];

// 9. 流动性硬隔离常数
export const LIQUIDITY_DISCOUNT_FACTOR = 0.5; // 未来 1-3 年确定性支出折减系数 50%
export const LIQUIDITY_SAFE_COVERAGE_RATIO = 1.5; // 短期应急流动性安全倍数底线 1.5 倍

// 10. 三重集中度检查阈值
export const CONCENTRATION_LIMITS = {
  singleAssetYellow: 40,     // 单一标的 >40% 黄灯
  top3AssetsRed: 70,         // 前三大标的合计 >70% 红灯
  marketCurrencyAlert: 60,   // 任一市场/币种 >60% 提示
  dividendStyleClusterAlert: 50 // 红利低波风格簇合计 >50% 提示
};

// 初始全局状态树 (全面纳入新模块)
export const INITIAL_STATE = {
  // 看板参数
  board: {
    principal: 50.0,        // 可用总本金 (万元)
    bufferSeed: 5.0,        // 缓冲池初始资金 (万元)
    targetMonthly: 0.2,     // 期望月现金流 (万元)
    growthRate: 6.5,        // 增长预期年化收益率 (%)
    moneyMarketRate: 2.0,   // 缓冲池闲置资金年化 (%)
    assets: DEFAULT_ASSETS
  },
  // 家庭资产体检
  health: {
    monthlyIncome: 30000,         // 家庭月收入 (元)
    monthlyExpense: 18000,        // 家庭月总支出 (元)
    essentialMonthlyExpense: 12000, // 月必要支出底线 (元，生活必需非弹性)
    monthlySurplus: 12000,        // 月可结余 (元)
    bucket1y: 100000,             // 1年内: 应急活期/流动资金 (元)
    bucket1To3y: 150000,          // 1-3年: 确定要用的钱/短期确定性资金 (元)
    bucket3To5y: 200000,          // 3-5年: 稳健配置 (元)
    bucket5yPlus: 500000,         // 5年以上: 长期权益/红利资产 (元)
    hasHousePlan: false,          // 是否有买房/换房计划
    expectedDownPayment: 600000   // 预计首付金额 (元)
  },
  // 1. 家庭保障缺口模块
  insurance: {
    coverageTier: 'insufficient',  // 保障自评档位: none / insufficient / moderate / complete
    stabilityTier: 'medium',       // 行业稳定性: high / medium / low
    childEduTarget: 500000,        // 子女教育金刚性储备诉求 (元)
    existingLifeCover: 500000,     // 已有寿险保额 (元)
    existingCritCover: 200000,     // 已有重疾保额 (元)
    existingAccidentCover: 500000, // 已有意外险保额 (元)
    hasMillionMedical: false       // 是否持有百万医疗兜底
  },
  // 3. 债务与决策模块
  debt: {
    mortgageBalance: 800000,         // 房贷余额 (元)
    carLoanBalance: 0,               // 车贷余额 (元)
    consumerLoanBalance: 0,          // 消费贷余额 (元)
    businessLoanBalance: 0,          // 经营贷余额 (元)
    monthlyDebtPayment: 4500,        // 每月贷款总还款 (元)
    debtRateBracket: '4.5-6%',       // 综合贷款利率区间 (<3.5% / 3.5-4.5% / 4.5-6% / >6%)
    customDebtRate: 5.5,             // 用户自报或选定档位利率 (%)
    highInterestDebtBalance: 0,      // 高息债务余额 (元)
    availableFundX: 200000           // 模拟可用资金 X (元)
  },
  // 4. 个人养老金税优模块
  pension: {
    hasAccount: true,                // 是否已开立个人养老金账户
    currentYearDeposited: 4000,      // 本年已缴存金额 (元, 0-12000)
    marginalTaxRate: 0.20            // 个人边际税率档位
  },
  // 5. 房产资产模块
  property: {
    totalEstimatedValue: 2800000,    // 房产当前总估值 (元)
    stressDropPct: 20                // 压力测试房产下跌幅度 (%)
  },
  // 6. 复合压力测试场景
  stress: {
    scenarioType: 'preset',          // preset | replay
    selectedPresetId: 'standard',    // standard | severe | stagflation
    selectedReplayId: 'replay_2018'  // replay_2018 | replay_2022 | replay_2015
  },
  // 7. 行为约束问卷
  behavior: {
    drawdownBracket: '10-20%',       // 自评最大承受回撤: <5%, 5-10%, 10-20%, 20-30%, >30%
    marketDropReaction: 'panic_sell', // 大跌第一反应: panic_sell | pause_watch | buy_more
    cashflowRelianceHigh: true,      // 现金流是否高度依赖投资收益
    industryVolatileHigh: false      // 行业波动大且失业恢复>6个月
  },
  // 8. 估值温度计与再平衡
  thermometer: {
    selectedIndex: 'csi_div_low_vol', // 跟踪指数
    percentile: 85,                   // 当前指数估值百分位 (0-100)
    userHoldings: {
      '512890': 15.0,
      '515450': 10.0,
      '513530': 8.0,
      '600941': 5.0,
      '600900': 4.0,
      '601398': 4.0,
      '601088': 3.0,
      '601668': 3.0
    }
  },
  // 2. 目标列表
  goals: [
    {
      id: 'goal-edu-2035',
      name: '2035 年子女教育金',
      type: '子女教育金',
      targetAmount: 1000000, // 100 万元
      targetYear: 2035,
      priority: '刚性',
      reservedAmount: 0,
      linkTo1To3y: false,
      retireConfig: {
        currentAge: 35,
        retireAge: 50,
        retireMonthlyExpense: 10000
      }
    },
    {
      id: 'goal-fire-2040',
      name: '2040 提前退休计划',
      type: '提前退休',
      targetAmount: 2500000, // 250 万元
      targetYear: 2040,
      priority: '弹性',
      reservedAmount: 150000,
      linkTo1To3y: true,
      retireConfig: {
        currentAge: 35,
        retireAge: 50,
        retireMonthlyExpense: 12000
      }
    }
  ]
};

export const DISCLAIMER_TEXT = "免责声明：所有财务推演与量化模型均基于用户输入的数据及假设性收益率，不代表任何历史业绩保证或未来投资收益承诺，不构成具体金融产品推荐。市场有风险，投资决策需审慎。";
