/**
 * Portfolio Engine (JavaScript Version)
 * Core financial calculations for asset allocation, cash flow projection,
 * valuation adjustments, stress testing, and family diagnostics.
 */

const portfolioEngine = {
    // 1. 组合收益测算
    calculatePortfolio(weights, assets, principal, bufferSeed, moneyMarketRate) {
        const investPrincipal = Math.max(principal - bufferSeed, 0.0);
        let totalWeight = 0.0;
        let blendedCashYield = 0.0;     // 现金流收益率 (仅统计 dividend 和 cash_interest)
        let blendedGrowthReturn = 0.0;  // 增长预期收益率 (仅统计 capital_growth)
        let blendedTotalReturn = 0.0;   // 综合年化收益率 (统计全部)

        const assetDetails = [];

        Object.keys(assets).forEach(code => {
            const asset = assets[code];
            const weight = parseFloat(weights[code]) || 0.0;
            totalWeight += weight;

            // 价格与当前股息率
            const currentPrice = asset.price || 0.0;
            const currentYield = asset.yield !== undefined ? asset.yield : asset.estimated_yield;
            const estReturn = asset.estimated_return !== undefined ? asset.estimated_return : currentYield;

            // 分配金额与预计年化/月化分红
            const allocatedAmt = investPrincipal * (weight / 100.0);
            const expectedAnnualDiv = allocatedAmt * (currentYield / 100.0) * 10000; // 元

            assetDetails.push({
                code: code,
                name: asset.name,
                role: asset.role,
                market: asset.market,
                volatility_level: asset.volatility_level,
                income_type: asset.income_type,
                weight: weight,
                price: currentPrice,
                yield: currentYield,
                estimated_return: estReturn,
                allocatedAmt: allocatedAmt,
                expectedAnnualDiv: expectedAnnualDiv,
                strategy_note: asset.strategy_note,
                risk_note: asset.risk_note
            });

            // 收益率累加分摊到各个口径
            if (asset.income_type === 'dividend' || asset.income_type === 'cash_interest') {
                blendedCashYield += (weight / 100.0) * currentYield;
            }
            if (asset.income_type === 'capital_growth') {
                blendedGrowthReturn += (weight / 100.0) * estReturn;
            }
            // 综合收益累加 (使用 estimated_return 衡量总回报)
            blendedTotalReturn += (weight / 100.0) * estReturn;
        });

        const expectedAnnualDividend = investPrincipal * (blendedCashYield / 100.0) * 10000; // 元
        const expectedMonthlyDividend = expectedAnnualDividend / 12.0; // 元
        const expectedMonthlyGrowth = investPrincipal * (blendedGrowthReturn / 100.0) * 10000 / 12.0; // 元

        return {
            investPrincipal,
            totalWeight,
            blendedCashYield,
            blendedGrowthReturn,
            blendedTotalReturn,
            expectedAnnualDividend,
            expectedMonthlyDividend,
            expectedMonthlyGrowth,
            assetDetails
        };
    },

    // 2. 36个月缓冲池流转模拟
    simulateCashflow(monthsRange, monthlyWithdraw, bufferSeed, investPrincipal, weights, assets, moneyMarketRate, rebalanceHarvest) {
        const bufferBalance = [bufferSeed * 10000.0]; // 元
        const dividendsHistory = [];
        const interestEarnedHistory = [];
        const harvestHistory = [];
        let breachedAtMonth = null;

        for (let t = 1; t <= monthsRange; t++) {
            const cMonth = ((t - 1) % 12) + 1;

            // 1) 计算当月常规分红流入 (仅针对 income_type 为 dividend 或 cash_interest 的资产)
            let monthDividend = 0.0;
            Object.keys(assets).forEach(code => {
                const asset = assets[code];
                const weight = parseFloat(weights[code]) || 0.0;
                const currentYield = asset.yield !== undefined ? asset.yield : asset.estimated_yield;

                if (asset.income_type === 'dividend' || asset.income_type === 'cash_interest') {
                    const distMonths = asset.distribution_months || asset.months || {};
                    const monthDistRatio = distMonths[cMonth.toString()] || 0.0;
                    if (monthDistRatio > 0.0) {
                        const assetValue = investPrincipal * (weight / 100.0) * 10000.0; // 元
                        monthDividend += assetValue * (currentYield / 100.0) * monthDistRatio;
                    }
                }
            });

            // 2) 年度再平衡超额成长变现 (Harvest) 机制
            let monthHarvest = 0.0;
            if (rebalanceHarvest && t % 12 === 0) {
                // 每满12个月，把所有 capital_growth 资产当年产生的增值部分变现
                Object.keys(assets).forEach(code => {
                    const asset = assets[code];
                    const weight = parseFloat(weights[code]) || 0.0;
                    if (asset.income_type === 'capital_growth') {
                        const estReturn = asset.estimated_return || 8.0;
                        const assetValue = investPrincipal * (weight / 100.0) * 10000.0; // 元
                        // 假设实现其设定的预期成长年收益
                        monthHarvest += assetValue * (estReturn / 100.0);
                    }
                });
            }

            // 3) 缓冲池利息 (月度利息)
            const currentInterest = bufferBalance[bufferBalance.length - 1] * (moneyMarketRate / 12.0);

            // 4) 缓冲池结转
            const nextBalance = bufferBalance[bufferBalance.length - 1] + monthDividend + monthHarvest + currentInterest - monthlyWithdraw;

            dividendsHistory.append ? dividendsHistory.append(monthDividend) : dividendsHistory.push(monthDividend);
            interestEarnedHistory.push(currentInterest);
            harvestHistory.push(monthHarvest);
            bufferBalance.push(nextBalance);

            if (nextBalance < 0 && breachedAtMonth === null) {
                breachedAtMonth = t;
            }
        }

        // 去除多余的最后一个期末余额
        const bufferHistory = bufferBalance.slice(0, monthsRange);

        return {
            bufferHistory,
            dividendsHistory,
            interestEarnedHistory,
            harvestHistory,
            breachedAtMonth,
            minBuffer: Math.min(...bufferHistory)
        };
    },

    // 3. 估值分位温度计与 DCA 调节因子
    getDcaAdjustment(historyData, indexCode, role) {
        if (!historyData || historyData.length === 0) {
            return {
                hasHistory: false,
                percentile: 50.0,
                factor: 1.0,
                pe: "--",
                pb: "--",
                dividend_yield: "--",
                valuationZone: "数据不足，保持基础计划",
                tips: "由于未找到此标的的估值历史序列，系统将采用基础配置计划，不进行动态调节。"
            };
        }

        // 过滤对应的 indexCode
        const filtered = historyData.filter(item => item.index_code === indexCode);
        if (filtered.length === 0) {
            return {
                hasHistory: false,
                percentile: 50.0,
                factor: 1.0,
                pe: "--",
                pb: "--",
                dividend_yield: "--",
                valuationZone: "数据不足，保持基础计划",
                tips: "由于未找到此标的的估值历史序列，系统将采用基础配置计划，不进行动态调节。"
            };
        }

        // 按日期升序排序
        filtered.sort((a, b) => new Date(a.date) - new Date(b.date));
        const latest = filtered[filtered.length - 1];
        const peList = filtered.map(item => parseFloat(item.pe)).filter(v => !isNaN(v));
        const pbList = filtered.map(item => parseFloat(item.pb)).filter(v => !isNaN(v));
        const dyList = filtered.map(item => parseFloat(item.dividend_yield)).filter(v => !isNaN(v));

        const currentPE = parseFloat(latest.pe);
        const currentPB = parseFloat(latest.pb);
        const currentDY = parseFloat(latest.dividend_yield);

        let percentile = 50.0;
        let factor = 1.0;
        let valuationZone = "合理估值区间 (估值适中)";
        let tips = "";

        // 根据资产角色使用不同的核心估值百分位判断指标
        if (role === 'dividend_income') {
            // 红利看股息率高低进行加仓调节（股息率越高代表估值越便宜）
            const count = dyList.filter(y => y < currentDY).length;
            percentile = parseFloat(((count / dyList.length) * 100).toFixed(1));

            if (percentile >= 70.0) {
                valuationZone = "极具性价比 (低估区域)";
                factor = 1.3;
                tips = "提示：目前红利资产股息率处于历史较高百分位，具备优秀的派息性价比，定投系数已调升至 1.3x。";
            } else if (percentile >= 30.0) {
                valuationZone = "合理估值区间 (估值中性)";
                factor = 1.0;
                tips = "提示：估值处于常态百分位，建议保持基础定投计划，定投系数 1.0x。";
            } else {
                valuationZone = "估值偏贵区间 (高估区域)";
                factor = 0.5;
                tips = "提示：股息率已被估值上涨稀释，性价比偏低，定投系数下调至 0.5x 以控制建仓成本。";
            }
        } else if (role === 'domestic_beta') {
            // 宽基看 PE/PB 估值百分位（PE 越低代表越低估，低估时定投调高）
            const count = peList.filter(p => p < currentPE).length;
            percentile = parseFloat(((count / peList.length) * 100).toFixed(1));

            if (percentile <= 30.0) {
                valuationZone = "极具性价比 (国内宽基低估)";
                factor = 1.2;
                tips = "提示：沪深300指数估值处于历史低估分位，长期配置性价比凸显，定投系数上调至 1.2x。";
            } else if (percentile <= 70.0) {
                valuationZone = "合理估值区间 (估值中性)";
                factor = 1.0;
                tips = "提示：宽基估值处于历史常态水平，建议按基础定投稳步积累，系数 1.0x。";
            } else {
                valuationZone = "估值偏贵区间 (宽基估值高企)";
                factor = 0.6;
                tips = "提示：沪深300估值已进入历史高估区域，适当下调定投金额，系数 0.6x。";
            }
        } else if (role === 'tech_growth') {
            // 科技成长看估值和波动回撤区间
            const count = peList.filter(p => p < currentPE).length;
            percentile = parseFloat(((count / peList.length) * 100).toFixed(1));

            if (percentile <= 25.0) {
                valuationZone = "超跌低估区间 (科技成长蓄势)";
                factor = 1.3;
                tips = "提示：科技类资产估值进入历史极低分水位，具备极强向上增长弹性，定投系数调高至 1.3x。";
            } else if (percentile <= 75.0) {
                valuationZone = "合理估值区间 (估值中性)";
                factor = 1.0;
                tips = "提示：科技指数估值温和，建议保持常规的小额定投频率，定投系数 1.0x。";
            } else {
                valuationZone = "情绪过热区间 (科技估值透支)";
                factor = 0.4;
                tips = "提示：科技成长股情绪过热，估值高位溢价，为防范高位被套，定投系数下调至 0.4x。";
            }
        } else if (role === 'overseas_beta') {
            // 海外宽基看估值和汇率风险
            const count = peList.filter(p => p < currentPE).length;
            percentile = parseFloat(((count / peList.length) * 100).toFixed(1));

            if (percentile <= 30.0) {
                valuationZone = "低估配置区域 (海外宽基低估)";
                factor = 1.1;
                tips = "提示：海外指数估值偏低，定投系数微调至 1.1x。注意换汇点位，人民币过弱时溢价风险增加。";
            } else if (percentile <= 70.0) {
                valuationZone = "合理估值区间 (估值中性)";
                factor = 1.0;
                tips = "提示：海外宽基估值合理，定投系数 1.0x。建议分批换汇以平滑汇率波动。";
            } else {
                valuationZone = "高估警戒区域 (海外宽基高估)";
                factor = 0.5;
                tips = "提示：海外指数市盈率偏高，定投系数降低至 0.5x。防止高位接盘和人民币贬值被套双重风险。";
            }
        }

        return {
            hasHistory: true,
            percentile,
            factor,
            pe: currentPE.toFixed(2),
            pb: currentPB.toFixed(2),
            dividend_yield: currentDY.toFixed(2) + "%",
            valuationZone,
            tips
        };
    },

    // 4. 极端市况压力测试
    runStressTest(weights, assets, investPrincipal, monthlyWithdraw, bufferMonths, moneyMarketRate, stressParams) {
        const startBuffer = bufferMonths * monthlyWithdraw;
        const stressBufferBalance = [startBuffer];
        const stressDividendsHistory = [];
        const interestEarnedHistory = [];
        let breachedAtMonth = null;
        const monthsRange = 36;

        // 计算压力下总资产的期初和压力回撤后的市值
        let initialPortfolioVal = investPrincipal * 10000.0; // 元
        let stressedPortfolioVal = 0.0; // 元

        Object.keys(assets).forEach(code => {
            const asset = assets[code];
            const weight = parseFloat(weights[code]) || 0.0;
            const assetVal = initialPortfolioVal * (weight / 100.0);

            // 获取该角色对应的压力回撤比率
            const role = asset.role;
            const drawdownRatio = stressParams.drawdown[role] !== undefined ? stressParams.drawdown[role] : 30.0; // 默认回撤30%
            stressedPortfolioVal += assetVal * (1.0 - drawdownRatio / 100.0);
        });

        // 组合最大总回撤计算
        const maxNetWorthDrawdown = ((initialPortfolioVal - stressedPortfolioVal) / initialPortfolioVal) * 100.0;

        // 模拟压力下的缓冲池流转
        for (let t = 1; t <= monthsRange; t++) {
            const cMonth = ((t - 1) % 12) + 1;

            // 现金分红流入 (受分红下降折损影响)
            let monthDividend = 0.0;
            Object.keys(assets).forEach(code => {
                const asset = assets[code];
                const weight = parseFloat(weights[code]) || 0.0;
                const currentYield = asset.yield !== undefined ? asset.yield : asset.estimated_yield;

                if (asset.income_type === 'dividend' || asset.income_type === 'cash_interest') {
                    const distMonths = asset.distribution_months || asset.months || {};
                    const monthDistRatio = distMonths[cMonth.toString()] || 0.0;
                    if (monthDistRatio > 0.0) {
                        const assetVal = investPrincipal * (weight / 100.0) * 10000.0; // 元
                        
                        // 资产回撤后的价值
                        const role = asset.role;
                        const assetDrawdown = stressParams.drawdown[role] !== undefined ? stressParams.drawdown[role] : 30.0;
                        const stressedAssetVal = assetVal * (1.0 - assetDrawdown / 100.0);

                        // 分红率下降折损
                        const divDrop = stressParams.dividendDrop[role] !== undefined ? stressParams.dividendDrop[role] : 20.0;
                        const stressedYield = currentYield * (1.0 - divDrop / 100.0);

                        monthDividend += stressedAssetVal * (stressedYield / 100.0) * monthDistRatio;
                    }
                }
            });

            // 缓冲池利息 (月度利息)
            const currentInterest = stressBufferBalance[stressBufferBalance.length - 1] * (moneyMarketRate / 12.0);

            // 缓冲池期末
            const nextBalance = stressBufferBalance[stressBufferBalance.length - 1] + monthDividend + currentInterest - monthlyWithdraw;

            stressDividendsHistory.push(monthDividend);
            interestEarnedHistory.push(currentInterest);
            stressBufferBalance.push(nextBalance);

            if (nextBalance < 0 && breachedAtMonth === null) {
                breachedAtMonth = t;
            }
        }

        const stressedBufferHistory = stressBufferBalance.slice(0, monthsRange);

        return {
            stressedBufferHistory,
            stressDividendsHistory,
            interestEarnedHistory,
            breachedAtMonth,
            maxNetWorthDrawdown,
            isBreached: breachedAtMonth !== null,
            minStressedBuffer: Math.min(...stressedBufferHistory)
        };
    },

    // 5. 家庭财务画像体检
    evaluateFamilyProfile(fd, investableAssets, netWorth, totalAssets, leverage, repayIncomeRatio, surplusRatio, cashCoverageMonths, investmentGoalCodes, riskToleranceCode) {
        // 画像判定优先次序
        let profileKey = "balanced";
        let profileTitle = "⚖️ 均衡发展型家庭";
        let profileDiag = "家庭资产负债结构中性，流动性防线与增长资产比例处于大致平稳的状态。";
        let quote = "“维护资产流动性与成长性的平衡是长胜法则。不要冒无谓的风险，用纪律抵抗市场情绪。”";
        let borderColor = "var(--text-secondary)";

        // 默认资产防线比例 (安全防线, 长期成长, 综合对冲)
        let safety = 30;
        let longterm = 50;
        let hedge = 20;
        let reason = "红利负责稳健派息现金流，宽基与科技负责博取长期增值弹性，黄金对冲极端宏观不确定性，现金缓冲锁定日常开销，确保家庭无被迫割肉变现之忧。";

        const hasShortTermLargeExpense = fd['expense-buyhouse'] || fd['expense-edu'] || fd['expense-med'] || fd['expense-biz'] || fd['expense-city'] || fd['expense-other'];

        // 核心财务健康判定
        const isLowCash = cashCoverageMonths < 6;
        const isHighDebt = leverage > 0.5 || repayIncomeRatio > 0.35;
        const isLowSurplus = surplusRatio < 0.15;

        // 积极成长型阻断校验
        const isProhibitAggressive = isLowCash || isHighDebt || isLowSurplus;

        if (isHighDebt) {
            profileKey = "leverage";
            profileTitle = "🚨 债务高锁型家庭";
            profileDiag = "家庭负债率偏高，或每月贷款偿还比例已超出安全红线，现金流极易断裂。";
            quote = "“别让时间约束变成情绪惩罚。高额负债不仅锁死了本金弹性，更放大了市场大跌时的心理恐慌。”";
            borderColor = "var(--accent-red)";
            safety = 50; longterm = 30; hedge = 20;
            reason = "鉴于家庭负债偏高，安全防御资产应占据首要核心位置（50%），限制或禁止高波动的科技/海外成长性配置，防止市场下行与偿债支出重叠时被动清仓。";
        } else if (isLowCash || isLowSurplus) {
            profileKey = "tight";
            profileTitle = "⚠️ 现金流脆弱型家庭";
            profileDiag = "月度储蓄率不足，或者应急备用金储备少于6个月固定生活费。";
            quote = "“现金不是最便宜的资产，它是让你在市场底部拿到留在牌桌上的入场券。优先充实池水。”";
            borderColor = "var(--accent-red)";
            safety = 60; longterm = 20; hedge = 20;
            reason = "优先使用流动资产和红利低波资产积攒至少12个月的应急现金防御墙（安全桶拉升至60%），待收支结余率与现金池充裕后，再逐步增配增长资产。";
        } else if (cashCoverageMonths >= 12 && surplusRatio >= 0.25 && riskToleranceCode >= 5) {
            // 允许提高宽基/科技成长等增长资产比例 (结余率高、现金富余、投资期限偏长)
            profileKey = "stable";
            profileTitle = "💎 稳健积累型家庭";
            profileDiag = "负债水平极低，每月结余能力强，且手握超过一年的固定开支现金储备，具备扎实的抗冲击底气。";
            quote = "“这类家庭拥有极高的财务喘息空间，可以更加注重长期大类资产配置的‘再平衡纪律’，分享企业增长红利。”";
            borderColor = "var(--accent-emerald)";
            safety = 20; longterm = 65; hedge = 15;
            reason = "由于财务底子扎实且风险承受期长，可缩减安全备用金至 20%，增配国内沪深300（经济Beta）、纳斯达克/科创50（科技增长）以及黄金对冲，最大化分享复利增值。";
        } else if (investableAssets > 0.0 && ((fd['ast-cash'] + fd['ast-mmf']) / investableAssets) > 0.7 && !hasShortTermLargeExpense) {
            profileKey = "conservative";
            profileTitle = "🛡️ 现金沉淀型家庭";
            profileDiag = "家庭极度保守，绝大部分可投资资产以现金或货币基金沉淀，未能建立对抗通胀的被动权益防线。";
            quote = "“全存现金的风险在于通货膨胀对实际购买力的隐性吞噬。安全感不应以未来购买力的缩水为隐性代价。”";
            borderColor = "var(--accent-blue)";
            safety = 30; longterm = 55; hedge = 15;
            reason = "保留 6-12 个月应急现金，将其余长期闲置的积淀现金分批配置到被动宽基（国内+海外）和红利低波指基中，获取 6%~8% 的加权年化回报以战胜通胀风险。";
        }

        return {
            profileKey,
            profileTitle,
            profileDiag,
            quote,
            borderColor,
            safety,
            longterm,
            hedge,
            reason,
            isProhibitAggressive
        };
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = portfolioEngine;
} else {
    window.portfolioEngine = portfolioEngine;
}
