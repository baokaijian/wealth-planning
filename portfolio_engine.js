/**
 * Portfolio Engine (JavaScript Version)
 * Core financial calculations for asset allocation, cash flow projection,
 * valuation adjustments, stress testing, and family diagnostics.
 */

const DEFAULT_RULES = {
    family_risk: { min_cash_coverage_months: 6.0, min_surplus_ratio: 0.15, max_repay_income_ratio: 0.35, max_leverage_ratio: 0.5 },
    concentration: { max_single_role: 45.0, max_single_market: 70.0, max_tech_roles: 25.0, max_dividend_role: 45.0, blocked_family_max_tech: 10.0 }
};
let planningRules = DEFAULT_RULES;
if (typeof module !== 'undefined' && module.exports) {
    try { planningRules = require('./planning_rules.json'); } catch (error) { planningRules = DEFAULT_RULES; }
}

const portfolioEngine = {
    setRules(rules) {
        planningRules = rules || DEFAULT_RULES;
    },
    isStableCashflowAsset(asset) {
        return asset.income_type === 'dividend' || asset.income_type === 'cash_interest';
    },

    evaluatePortfolioFit(weights, assets, isProhibitAggressive = false) {
        const roleWeights = {};
        const marketWeights = {};
        Object.entries(assets).forEach(([code, asset]) => {
            const weight = parseFloat(weights[code]) || 0.0;
            const role = asset.role || 'unknown';
            const market = asset.market || 'unknown';
            roleWeights[role] = (roleWeights[role] || 0.0) + weight;
            marketWeights[market] = (marketWeights[market] || 0.0) + weight;
        });
        const techWeight = (roleWeights.tech_growth || 0.0) + (roleWeights.overseas_tech || 0.0);
        const dividendWeight = roleWeights.dividend_income || 0.0;
        const messages = [];
        const limits = planningRules.concentration;
        Object.entries(roleWeights).forEach(([role, weight]) => {
            if (weight > limits.max_single_role) messages.push(`单一角色 ${role} 为 ${weight.toFixed(1)}%，超过 ${limits.max_single_role}%。`);
        });
        Object.entries(marketWeights).forEach(([market, weight]) => {
            if (weight > limits.max_single_market) messages.push(`单一市场 ${market} 为 ${weight.toFixed(1)}%，超过 ${limits.max_single_market}%。`);
        });
        if (techWeight > limits.max_tech_roles) messages.push(`科技相关资产为 ${techWeight.toFixed(1)}%，超过 ${limits.max_tech_roles}%。`);
        if (dividendWeight > limits.max_dividend_role) messages.push(`红利类资产为 ${dividendWeight.toFixed(1)}%，现金流底盘过厚，增长弹性不足。`);
        if (isProhibitAggressive && techWeight > limits.blocked_family_max_tech) messages.push('家庭体检已阻断积极型配置，科技相关资产应保持低权重。');
        return {
            isMatched: messages.length === 0,
            status: messages.length === 0 ? '与家庭防线匹配' : '需要降低集中度或风险暴露',
            messages,
            roleWeights,
            marketWeights,
            techWeight,
            dividendWeight
        };
    },

    // 1. 组合收益测算
    calculatePortfolio(weights, assets, principal, bufferSeed, moneyMarketRate) {
        const investPrincipal = Math.max(principal - bufferSeed, 0.0);
        let totalWeight = 0.0;
        let blendedCashYield = 0.0;     // 现金流收益率 (仅统计 dividend 和 cash_interest)
        let blendedGrowthReturn = 0.0;  // 增长预期收益率 (仅统计 capital_growth)
        let blendedTotalReturn = 0.0;   // 综合年化收益率 (统计全部)

        const assetDetails = [];

        const errors = [];
        const dataErrors = [];
        Object.keys(assets).forEach(code => {
            const asset = assets[code];
            const distributionValidation = this.validateDistributionMonths(asset);
            distributionValidation.errors.forEach(error => dataErrors.push(`${code}: ${error}`));
            const rawWeight = weights[code] === '' || weights[code] === null ? 0 : Number(weights[code]);
            const weight = Number.isFinite(rawWeight) ? rawWeight : 0.0;
            if (!Number.isFinite(rawWeight)) errors.push(`${code} 的权重不是有限数字。`);
            if (rawWeight < 0) errors.push(`${code} 的权重不能为负数。`);
            if (rawWeight > 100) errors.push(`${code} 的单一权重不能超过 100%。`);
            totalWeight += weight;

            // 价格与当前股息率
            const currentPrice = asset.price || 0.0;
            const currentYield = asset.impliedYield !== undefined ? asset.impliedYield : (asset.yield !== undefined ? asset.yield : asset.estimated_yield);
            const estReturn = asset.estimated_return !== undefined ? asset.estimated_return : currentYield;

            // 分配金额与预计年化/月化分红
            const allocatedAmt = investPrincipal * (weight / 100.0);
            const stableCashflow = this.isStableCashflowAsset(asset);
            const expectedAnnualDiv = stableCashflow ? allocatedAmt * (currentYield / 100.0) * 10000 : 0.0; // 元

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
                target_index_code: asset.target_index_code,
                rebalance_band: asset.rebalance_band || 3,
                stableCashflow,
                allocatedAmt: allocatedAmt,
                expectedAnnualDiv: expectedAnnualDiv,
                strategy_note: asset.strategy_note,
                risk_note: asset.risk_note
            });

            // 收益率累加分摊到各个口径
            if (stableCashflow) {
                blendedCashYield += (weight / 100.0) * currentYield;
            }
            if (asset.income_type === 'capital_growth') {
                blendedGrowthReturn += (weight / 100.0) * estReturn;
            }
            // 综合收益累加 (使用 estimated_return 衡量总回报)
            blendedTotalReturn += (weight / 100.0) * estReturn;
        });

        if (Math.abs(totalWeight - 100) > 0.01) {
            errors.push(`权重合计为 ${totalWeight.toFixed(2)}%，必须为 100%。`);
        }

        const expectedAnnualDividend = investPrincipal * (blendedCashYield / 100.0) * 10000; // 元
        const expectedMonthlyDividend = expectedAnnualDividend / 12.0; // 元
        const expectedMonthlyGrowth = investPrincipal * (blendedGrowthReturn / 100.0) * 10000 / 12.0; // 元

        return {
            valid: errors.length === 0,
            errors,
            dataErrors,
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

    getHarvestReturn(asset, harvestScenario) {
        if (harvestScenario === 'conservative') return -10.0;
        if (harvestScenario === 'neutral') return 3.0;
        if (harvestScenario === 'optimistic') return parseFloat(asset.estimated_return) || 0.0;
        return 0.0;
    },

    // 2. 36个月缓冲池流转模拟
    simulateCashflow(
        monthsRange,
        monthlyWithdraw,
        bufferSeed,
        investPrincipal,
        weights,
        assets,
        moneyMarketRate,
        rebalanceHarvest = false,
        harvestScenario = 'neutral',
        startMonth = 1,
        stableIncomeDrop = 0.0,
        delayMonths = 0,
        pauseDividendYear = false
    ) {
        const bufferBalance = [bufferSeed * 10000.0]; // 元
        const dividendIncomeHistory = [];
        const cashInterestIncomeHistory = [];
        const bufferInterestHistory = [];
        const harvestHistory = [];
        const totalStableIncomeHistory = [];
        const stableIncomeContributions = {
            byAsset: {},
            byRole: {},
            byMarket: {}
        };
        const scheduledStableIncome = Array.from(
            { length: monthsRange + Math.max(0, delayMonths) + 2 },
            () => []
        );
        let breachedAtMonth = null;
        const safeStartMonth = Math.min(Math.max(parseInt(startMonth) || 1, 1), 12);
        const incomeMultiplier = Math.max(0.0, 1.0 - ((parseFloat(stableIncomeDrop) || 0.0) / 100.0));
        const safeDelayMonths = Math.min(Math.max(parseInt(delayMonths) || 0, 0), 6);

        const addContribution = (asset, code, amount) => {
            if (amount <= 0) return;
            stableIncomeContributions.byAsset[code] = stableIncomeContributions.byAsset[code] || {
                code,
                name: asset.name,
                amount: 0.0
            };
            stableIncomeContributions.byAsset[code].amount += amount;
            const role = asset.role || 'unknown';
            const market = asset.market || 'unknown';
            stableIncomeContributions.byRole[role] = (stableIncomeContributions.byRole[role] || 0.0) + amount;
            stableIncomeContributions.byMarket[market] = (stableIncomeContributions.byMarket[market] || 0.0) + amount;
        };

        for (let t = 1; t <= monthsRange; t++) {
            const cMonth = ((safeStartMonth - 1 + t - 1) % 12) + 1;

            // 1) 计算当月常规稳定收入，并按压力参数安排到账。
            Object.keys(assets).forEach(code => {
                const asset = assets[code];
                const weight = parseFloat(weights[code]) || 0.0;
                const currentYield = asset.impliedYield !== undefined ? asset.impliedYield : (asset.yield !== undefined ? asset.yield : asset.estimated_yield);

                if (this.isStableCashflowAsset(asset)) {
                    const distMonths = asset.distribution_months || asset.months || {};
                    const monthDistRatio = distMonths[cMonth.toString()] || 0.0;
                    if (monthDistRatio > 0.0) {
                        const isDividend = asset.income_type === 'dividend';
                        const isPausedDividend = pauseDividendYear && isDividend && t >= 13 && t <= 24;
                        const assetValue = investPrincipal * (weight / 100.0) * 10000.0; // 元
                        const amount = isPausedDividend ? 0.0 : assetValue * (currentYield / 100.0) * monthDistRatio * incomeMultiplier;
                        const arrivalMonth = t + safeDelayMonths;
                        if (amount > 0.0 && arrivalMonth <= monthsRange) {
                            scheduledStableIncome[arrivalMonth].push({
                                code,
                                asset,
                                amount,
                                kind: isDividend ? 'dividend' : 'cash_interest'
                            });
                        }
                    }
                }
            });

            let monthDividend = 0.0;
            let monthCashInterest = 0.0;
            scheduledStableIncome[t].forEach(item => {
                if (item.kind === 'dividend') {
                    monthDividend += item.amount;
                } else {
                    monthCashInterest += item.amount;
                }
                addContribution(item.asset, item.code, item.amount);
            });

            // 2) 情景假设下卖出成长资产补充现金流。默认关闭，安全结论不依赖该项。
            let monthHarvest = 0.0;
            if (rebalanceHarvest && t % 12 === 0) {
                Object.keys(assets).forEach(code => {
                    const asset = assets[code];
                    const weight = parseFloat(weights[code]) || 0.0;
                    if (asset.income_type === 'capital_growth') {
                        const scenarioReturn = this.getHarvestReturn(asset, harvestScenario);
                        if (scenarioReturn <= 0) return;
                        const assetValue = investPrincipal * (weight / 100.0) * 10000.0; // 元
                        monthHarvest += assetValue * (scenarioReturn / 100.0);
                    }
                });
            }

            // 3) 缓冲池利息 (月度利息)
            const currentInterest = bufferBalance[bufferBalance.length - 1] * (moneyMarketRate / 12.0);
            const monthStableIncome = monthDividend + monthCashInterest + currentInterest;

            // 4) 缓冲池结转
            const nextBalance = bufferBalance[bufferBalance.length - 1] + monthStableIncome + monthHarvest - monthlyWithdraw;

            dividendIncomeHistory.push(monthDividend);
            cashInterestIncomeHistory.push(monthCashInterest);
            bufferInterestHistory.push(currentInterest);
            harvestHistory.push(monthHarvest);
            totalStableIncomeHistory.push(monthStableIncome);
            bufferBalance.push(nextBalance);

            if (nextBalance < 0 && breachedAtMonth === null) {
                breachedAtMonth = t;
            }
        }

        const bufferHistory = bufferBalance.slice(1);
        const minBuffer = Math.min(...bufferHistory);
        const minBufferMonth = bufferHistory.indexOf(minBuffer) + 1;

        return {
            bufferHistory,
            dividendIncomeHistory,
            cashInterestIncomeHistory,
            bufferInterestHistory,
            harvestHistory,
            totalStableIncomeHistory,
            stableIncomeContributions,
            // Backward-compatible aliases for older call sites.
            dividendsHistory: totalStableIncomeHistory,
            interestEarnedHistory: bufferInterestHistory,
            breachedAtMonth,
            minBuffer,
            minBufferMonth
        };
    },

    calculateCashflowFeasibility(
        monthsRange,
        targetMonthlyWithdraw,
        bufferSeed,
        principal,
        weights,
        assets,
        moneyMarketRate,
        startMonth = 1,
        stableIncomeDrop = 0.0,
        delayMonths = 0,
        pauseDividendYear = false
    ) {
        const survives = (testMonthly, testPrincipal, testBufferSeed) => {
            const investPrincipal = Math.max(testPrincipal - testBufferSeed, 0.0);
            const sim = this.simulateCashflow(
                monthsRange,
                testMonthly,
                testBufferSeed,
                investPrincipal,
                weights,
                assets,
                moneyMarketRate,
                false,
                'neutral',
                startMonth,
                stableIncomeDrop,
                delayMonths,
                pauseDividendYear
            );
            return sim.minBuffer > 0;
        };

        let low = 0.0;
        let high = Math.max(targetMonthlyWithdraw, 1.0);
        const maxSearchMonthly = 1e9;
        let searchCapped = false;
        while (survives(high, principal, bufferSeed) && high < maxSearchMonthly) {
            low = high;
            high = Math.min(high * 2, maxSearchMonthly);
        }
        if (high >= maxSearchMonthly && survives(high, principal, bufferSeed)) searchCapped = true;
        for (let i = 0; i < 40; i++) {
            const mid = (low + high) / 2.0;
            if (survives(mid, principal, bufferSeed)) low = mid;
            else high = mid;
        }

        let minPrincipal = principal;
        if (targetMonthlyWithdraw > 0 && !survives(targetMonthlyWithdraw, principal, bufferSeed)) {
            let lowP = Math.max(bufferSeed, 0.0);
            let highP = Math.max(principal, bufferSeed + 1.0);
            while (!survives(targetMonthlyWithdraw, highP, bufferSeed) && highP < 100000.0) {
                highP *= 1.5;
                if (highP <= bufferSeed) highP = bufferSeed + 1.0;
            }
            if (highP < 100000.0) {
                for (let i = 0; i < 40; i++) {
                    const mid = (lowP + highP) / 2.0;
                    if (survives(targetMonthlyWithdraw, mid, bufferSeed)) highP = mid;
                    else lowP = mid;
                }
                minPrincipal = highP;
            } else {
                minPrincipal = null;
            }
        }

        // 追加缓冲资金不挤占既有投资本金。逐月扫描避免依赖未证明的单调性。
        let minBufferMonths = 0.0;
        let minAdditionalBufferWan = 0.0;
        if (targetMonthlyWithdraw > 0) {
            const fixedInvestPrincipal = Math.max(principal - bufferSeed, 0.0);
            const survivesWithAdditionalBuffer = additionalWan => {
                const sim = this.simulateCashflow(
                    monthsRange, targetMonthlyWithdraw, bufferSeed + additionalWan,
                    fixedInvestPrincipal, weights, assets, moneyMarketRate, false, 'neutral',
                    startMonth, stableIncomeDrop, delayMonths, pauseDividendYear
                );
                return sim.minBuffer > 0;
            };
            if (survivesWithAdditionalBuffer(0)) {
                minBufferMonths = 0.0;
            } else {
                minBufferMonths = null;
                minAdditionalBufferWan = null;
                for (let month = 1; month <= 120; month++) {
                    const extra = month * targetMonthlyWithdraw / 10000.0;
                    if (survivesWithAdditionalBuffer(extra)) {
                        minBufferMonths = month;
                        minAdditionalBufferWan = extra;
                        break;
                    }
                }
            }
        }

        return {
            safeMonthlyWithdraw: low,
            safeMonthlyWithdrawWan: low / 10000.0,
            recommendedMonthlyExpense: low * 0.95,
            recommendedMonthlyExpenseWan: low * 0.95 / 10000.0,
            minPrincipalWan: minPrincipal,
            minBufferMonths,
            minAdditionalBufferWan,
            searchCapped,
            isTargetFeasibleWithoutHarvest: targetMonthlyWithdraw > 0 ? survives(targetMonthlyWithdraw, principal, bufferSeed) : true
        };
    },

    // 3. 估值分位温度计与 DCA 调节因子
    getDcaAdjustment(historyData, indexCode, role, context = {}) {
        const noHistoryResponse = () => {
            const roleMessages = {
                dividend_income: {
                    zone: "红利估值数据不足",
                    metric: "股息率历史"
                },
                domestic_beta: {
                    zone: "宽基估值数据不足",
                    metric: "PE/PB 历史"
                },
                tech_growth: {
                    zone: "科技成长估值数据不足",
                    metric: "PE/PB 历史"
                },
                overseas_broad: {
                    zone: "海外宽基估值数据不足",
                    metric: "本地估值历史"
                },
                overseas_tech: {
                    zone: "海外科技估值数据不足",
                    metric: "本地估值历史"
                },
                overseas_beta: {
                    zone: "海外权益估值数据不足",
                    metric: "本地估值历史"
                }
            };
            const roleMessage = roleMessages[role] || {
                zone: "估值数据不足",
                metric: "估值历史"
            };
            const overseasRiskTip = (role === 'overseas_broad' || role === 'overseas_tech' || role === 'overseas_beta')
                ? "注意汇率、QDII 溢价与跟踪误差风险。"
                : "";
            return {
                hasHistory: false,
                percentile: 50.0,
                factor: 1.0,
                pe: "--",
                pb: "--",
                dividend_yield: "--",
                valuationZone: `${roleMessage.zone}，保持基础计划`,
                tips: `由于未找到此标的的${roleMessage.metric}，DCA 保持 1.0x，不生成低估/高估判断。${overseasRiskTip}`
            };
        };
        if (!historyData || historyData.length === 0) {
            return noHistoryResponse();
        }

        // 过滤对应的 indexCode
        const filtered = historyData.filter(item => item.index_code === indexCode);
        if (filtered.length === 0) {
            return noHistoryResponse();
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
            const dividendWeight = parseFloat(context.dividendWeight || 0.0);
            const cashflowFeasible = context.cashflowFeasible !== false;
            if (factor > 1.0 && (dividendWeight > 45.0 || !cashflowFeasible)) {
                factor = 1.0;
                const capReason = dividendWeight > 45.0
                    ? "组合红利权重已超过 45%，即使股息率较高也不放大红利定投。"
                    : "现金缓冲池默认安全测试未通过，先补现金缓冲，不要因低估强行加仓。";
                tips += ` ${capReason}`;
            }
        } else if (role === 'domestic_beta') {
            // 宽基看 PE/PB 估值百分位（PE 越低代表越低估，低估时定投调高）
            const pePct = parseFloat(((peList.filter(p => p < currentPE).length / peList.length) * 100).toFixed(1));
            const pbPct = pbList.length > 0 ? parseFloat(((pbList.filter(p => p < currentPB).length / pbList.length) * 100).toFixed(1)) : pePct;
            percentile = Math.max(pePct, pbPct);

            if (percentile <= 30.0) {
                valuationZone = "极具性价比 (国内宽基低估)";
                factor = 1.2;
                tips = "提示：国内宽基 PE/PB 估值处于历史低位，长期配置性价比凸显，定投系数上调至 1.2x。";
            } else if (percentile <= 70.0) {
                valuationZone = "合理估值区间 (估值中性)";
                factor = 1.0;
                tips = "提示：宽基估值处于历史常态水平，建议按基础定投稳步积累，系数 1.0x。";
            } else {
                valuationZone = "估值偏贵区间 (宽基估值高企)";
                factor = 0.6;
                tips = "提示：国内宽基 PE/PB 已进入历史高估区域，适当下调定投金额，系数 0.6x。";
            }
        } else if (role === 'tech_growth') {
            // 科技成长看估值和波动回撤区间
            const count = peList.filter(p => p < currentPE).length;
            percentile = parseFloat(((count / peList.length) * 100).toFixed(1));

            if (percentile <= 25.0) {
                valuationZone = "超跌低估区间 (科技成长蓄势)";
                factor = 1.0;
                tips = "提示：科技类资产估值进入历史低位，但波动较高，定投系数最高不超过 1.0x。";
            } else if (percentile <= 75.0) {
                valuationZone = "合理估值区间 (估值中性)";
                factor = 0.8;
                tips = "提示：科技指数估值温和，但仍属于高波动资产，建议保持克制的小额定投，系数 0.8x。";
            } else {
                valuationZone = "情绪过热区间 (科技估值透支)";
                factor = 0.3;
                tips = "提示：科技成长股情绪过热，估值高位溢价，为防范高位被套，定投系数严格下调至 0.3x。";
            }
        } else if (role === 'overseas_broad' || role === 'overseas_tech' || role === 'overseas_beta') {
            if (peList.length === 0) {
                valuationZone = "海外估值数据不足";
                factor = 1.0;
                tips = "提示：当前缺少该海外资产的本地估值历史，保持 1.0x 基础计划，不生成低估/高估判断。注意汇率、QDII 溢价与跟踪误差风险。";
            } else if (role === 'overseas_tech') {
                const count = peList.filter(p => p < currentPE).length;
                percentile = parseFloat(((count / peList.length) * 100).toFixed(1));

                if (percentile <= 25.0) {
                    valuationZone = "海外科技估值低位";
                    factor = 1.0;
                    tips = "提示：海外科技低估时仍需控制集中度，定投系数不超过 1.0x。";
                } else if (percentile <= 75.0) {
                    valuationZone = "海外科技估值中性";
                    factor = 0.8;
                    tips = "提示：纳指100偏科技成长属性，估值中性时保持克制定投，系数 0.8x。";
                } else {
                    valuationZone = "海外科技估值偏贵";
                    factor = 0.3;
                    tips = "提示：海外科技高估时严格降温，系数 0.3x，并注意汇率与溢价风险。";
                }
            } else {
                const count = peList.filter(p => p < currentPE).length;
                percentile = parseFloat(((count / peList.length) * 100).toFixed(1));

                if (percentile <= 30.0) {
                    valuationZone = "低估配置区域 (海外宽基低估)";
                    factor = 1.0;
                    tips = "提示：海外宽基估值偏低，但因汇率、QDII 溢价、跟踪误差和数据覆盖限制，最高保持 1.0x。";
                } else if (percentile <= 70.0) {
                    valuationZone = "合理估值区间 (估值中性)";
                    factor = 1.0;
                    tips = "提示：海外宽基估值合理，定投系数 1.0x。建议分批换汇以平滑汇率波动。";
                } else {
                    valuationZone = "高估警戒区域 (海外宽基高估)";
                    factor = 0.5;
                    tips = "提示：海外指数市盈率偏高，定投系数降低至 0.5x。防止高位接盘和汇率波动双重风险。";
                }
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
        const portfolioDrawdown = initialPortfolioVal > 0
            ? ((initialPortfolioVal - stressedPortfolioVal) / initialPortfolioVal) * 100.0
            : 0.0;

        // 模拟压力下的缓冲池流转
        for (let t = 1; t <= monthsRange; t++) {
            const cMonth = ((t - 1) % 12) + 1;

            // 现金分红流入 (受分红下降折损影响)
            let monthDividend = 0.0;
            Object.keys(assets).forEach(code => {
                const asset = assets[code];
                const weight = parseFloat(weights[code]) || 0.0;
                const currentYield = asset.impliedYield !== undefined ? asset.impliedYield : (asset.yield !== undefined ? asset.yield : asset.estimated_yield);

                if (this.isStableCashflowAsset(asset)) {
                    const distMonths = asset.distribution_months || asset.months || {};
                    const monthDistRatio = distMonths[cMonth.toString()] || 0.0;
                    if (monthDistRatio > 0.0) {
                        const assetVal = investPrincipal * (weight / 100.0) * 10000.0; // 元
                        
                        // 现金分配以压力前持有份额和年度分配额为基数，市场回撤不重复折损现金流。
                        const role = asset.role;
                        const cashflowDrops = stressParams.cashflowDrop || stressParams.dividendDrop || {};
                        const typeDrop = asset.income_type === 'cash_interest'
                            ? (asset.role === 'cash' ? cashflowDrops.moneyMarket : cashflowDrops.bondCoupon)
                            : cashflowDrops.equityDividend;
                        const divDrop = cashflowDrops[role] !== undefined
                            ? cashflowDrops[role]
                            : (typeDrop !== undefined ? typeDrop : 20.0);
                        const stressedYield = currentYield * (1.0 - divDrop / 100.0);

                        monthDividend += assetVal * (stressedYield / 100.0) * monthDistRatio;
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

        const stressedBufferHistory = stressBufferBalance.slice(1);

        return {
            stressedBufferHistory,
            stressDividendsHistory,
            interestEarnedHistory,
            breachedAtMonth,
            portfolioDrawdown,
            maxNetWorthDrawdown: portfolioDrawdown,
            isBreached: breachedAtMonth !== null,
            minStressedBuffer: Math.min(...stressedBufferHistory)
        };
    },

    validateDistributionMonths(asset) {
        const errors = [];
        const months = asset.distribution_months || asset.months || {};
        let total = 0;
        Object.entries(months).forEach(([month, ratio]) => {
            const value = Number(ratio);
            if (!/^(?:[1-9]|1[0-2])$/.test(String(month))) errors.push(`无效分红月份：${month}`);
            if (!Number.isFinite(value) || value < 0 || value > 1) errors.push(`${month} 月分配比例无效。`);
            else total += value;
        });
        if (this.isStableCashflowAsset(asset) && Math.abs(total - 1) > 0.01) {
            errors.push(`分红月份比例合计为 ${total.toFixed(3)}，应为 1。`);
        }
        return { valid: errors.length === 0, errors, total };
    },

    calculateRebalancePlan({ holdings, targetWeights, rebalanceBands = {}, newCash = 0, incrementalMode = true }) {
        const codes = Array.from(new Set([...Object.keys(holdings || {}), ...Object.keys(targetWeights || {})]));
        const safeCash = Math.max(Number(newCash) || 0, 0);
        const currentTotal = codes.reduce((sum, code) => sum + Math.max(Number(holdings[code]) || 0, 0), 0);
        const postContributionTotal = currentTotal + safeCash;
        const rows = codes.map(code => {
            const holding = Math.max(Number(holdings[code]) || 0, 0);
            const targetPct = Number(targetWeights[code]) || 0;
            const targetValue = postContributionTotal * targetPct / 100;
            return { code, holding, targetPct, targetValue, gap: targetValue - holding, band: Number(rebalanceBands[code]) || 0, buyAmount: 0 };
        });
        // 资金不足时按缺口从大到小补足，结果直观且不会产生碎片化小额交易。
        let remaining = incrementalMode ? safeCash : 0;
        rows.filter(row => row.gap > 0).sort((a, b) => b.gap - a.gap).forEach(row => {
            row.buyAmount = Math.min(row.gap, remaining);
            remaining -= row.buyAmount;
        });
        const allocatedCash = safeCash - remaining;
        return {
            currentTotal, postContributionTotal, allocatedCash, unallocatedCash: remaining,
            rows: rows.map(row => {
                const postValue = row.holding + row.buyAmount;
                const beforePct = currentTotal > 0 ? row.holding / currentTotal * 100 : 0;
                const afterPct = postContributionTotal > 0 ? postValue / postContributionTotal * 100 : 0;
                const deviationPct = afterPct - row.targetPct;
                const outsideBand = Math.abs(deviationPct) > row.band;
                const sellAmount = outsideBand && deviationPct > 0 ? Math.max(postValue - row.targetValue, 0) : 0;
                return { ...row, beforePct, afterPct, deviationPct, outsideBand, sellAmount, suggestedAmount: row.buyAmount > 0 ? row.buyAmount : -sellAmount };
            })
        };
    },

    validateAndMigrateSnapshot(input) {
        const errors = [];
        if (!input || typeof input !== 'object' || Array.isArray(input)) return { valid: false, errors: ['快照必须是 JSON 对象。'] };
        const allowedTopLevel = ['version','schema','exportedAt','source','privacy','metrics','assumptions'];
        Object.keys(input).forEach(key => {
            if (!allowedTopLevel.includes(key)) errors.push(`未知顶层字段：${key}`);
        });
        if (![1, 2].includes(input.version)) errors.push('仅支持 version 1 或 2 快照。');
        if (input.version === 2 && input.schema !== 'wealth-planning-financial-plan') errors.push('快照 schema 不匹配。');
        if (typeof input.exportedAt !== 'string' || input.exportedAt.length > 100) errors.push('exportedAt 类型或长度无效。');
        if (!input.metrics || typeof input.metrics !== 'object' || Array.isArray(input.metrics)) errors.push('metrics 必须是对象。');
        const allowedMetrics = ['healthScore','safeMonthlyWithdrawWan','recommendedMonthlyExpenseWan','cashCoverageMonths','repayIncomeRatio','surplusRatio','stressBreached','stressMinBuffer'];
        Object.entries(input.metrics || {}).forEach(([key, value]) => {
            if (!allowedMetrics.includes(key)) errors.push(`未知 metrics 字段：${key}`);
            if (key !== 'stressBreached' && value !== null && (!Number.isFinite(Number(value)) || Math.abs(Number(value)) > 1e12)) errors.push(`${key} 数值无效。`);
            if (key === 'stressBreached' && typeof value !== 'boolean') errors.push('stressBreached 必须为布尔值。');
        });
        const allowedAssumptions = ['principalWan','targetMonthlyWan','bufferSeedWan','moneyMarketRatePct','dataSource','dataTimestamp'];
        if (input.assumptions !== undefined && (!input.assumptions || typeof input.assumptions !== 'object' || Array.isArray(input.assumptions))) {
            errors.push('assumptions 必须是对象。');
        }
        Object.entries(input.assumptions || {}).forEach(([key, value]) => {
            if (!allowedAssumptions.includes(key)) errors.push(`未知 assumptions 字段：${key}`);
            if (['principalWan','targetMonthlyWan','bufferSeedWan','moneyMarketRatePct'].includes(key)
                && (!Number.isFinite(Number(value)) || Number(value) < 0 || Number(value) > 1e9)) errors.push(`${key} 数值范围无效。`);
            if (['dataSource','dataTimestamp'].includes(key) && typeof value !== 'string') errors.push(`${key} 必须是字符串。`);
        });
        if (errors.length) return { valid: false, errors };
        const migrated = input.version === 1
            ? { ...input, version: 2, schema: 'wealth-planning-financial-plan', migratedFromVersion: 1, readOnlySource: true }
            : { ...input };
        return { valid: true, errors: [], snapshot: migrated };
    },

    // 5. 家庭财务画像体检
    calculateFourMoneyAnalysis(fd, totalAssets, netWorth, leverage, repayIncomeRatio, surplusRatio, cashCoverageMonths, riskToleranceCode) {
        const num = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
        const monthlyLivingExpense = Math.max(num(fd['f-fixed-expense']), 1);
        const monthlyEssentialExpense = Math.max(num(fd['f-essential-expense']), monthlyLivingExpense * 0.7, 1);
        const monthlyRequiredOutflow = monthlyEssentialExpense + num(fd['debt-monthly-repay']);
        const liquidCash = num(fd['ast-cash']) + num(fd['ast-mmf']);
        const plannedSpend12m = num(fd['f-planned-spend-12m']);
        const plannedSpend36m = num(fd['f-planned-spend-36m']);
        const highInterestDebt = num(fd['debt-high-interest']);
        const coverageLevel = fd['protect-coverage'] || 'basic';
        const hasLargeExpense = fd['expense-buyhouse'] || fd['expense-edu'] || fd['expense-med'] || fd['expense-biz'] || fd['expense-city'] || fd['expense-other'];
        const hasFamilyPressure = fd['f-children'] === 'yes' || fd['f-elders'] === 'yes' || fd['f-stability'] === 'volatile' || leverage > 0.45 || repayIncomeRatio > 0.3 || highInterestDebt > 0;

        const spendMinMonths = (hasLargeExpense || plannedSpend12m > 0) ? 6 : 2;
        const spendMaxMonths = (hasLargeExpense || plannedSpend36m > 0) ? 12 : 3;
        const lifeMinMonths = hasFamilyPressure ? 12 : 6;
        const lifeMaxMonths = hasFamilyPressure ? 18 : 12;

        const spendMin = Math.max(monthlyRequiredOutflow * spendMinMonths, plannedSpend12m);
        const spendMax = Math.max(monthlyRequiredOutflow * spendMaxMonths, plannedSpend12m + plannedSpend36m * 0.5);
        const spendAmount = Math.min(liquidCash, spendMax);
        const liquidAfterSpend = Math.max(0, liquidCash - spendAmount);

        const coverageCreditMonths = { none: 0, basic: 3, adequate: 6, strong: 9 }[coverageLevel] ?? 3;
        const protectionAdequacyMonths = coverageCreditMonths;
        const lifeMin = monthlyRequiredOutflow * lifeMinMonths;
        const lifeMax = monthlyRequiredOutflow * lifeMaxMonths;
        const lifeReserve = Math.min(liquidAfterSpend, lifeMax);
        const stableLiquidRemainder = Math.max(0, liquidAfterSpend - lifeReserve);

        const insuranceCashValue = num(fd['ast-insurance']);
        const insuranceLiquidityDiscount = 0.7;
        const discountedInsuranceCashValue = insuranceCashValue * insuranceLiquidityDiscount;
        const lifeAmount = lifeReserve + discountedInsuranceCashValue;
        const earnAmount = num(fd['ast-ashare']) + num(fd['ast-hk']) + num(fd['ast-overseas']) + num(fd['ast-others']);
        const preserveAmount = num(fd['ast-house']) + num(fd['ast-gold']) + stableLiquidRemainder;
        const baseAssets = Math.max(num(totalAssets), 1);

        let earnMinPct = 25;
        let earnMaxPct = 55;
        const familyLimits = planningRules.family_risk;
        if (cashCoverageMonths < familyLimits.min_cash_coverage_months || repayIncomeRatio > familyLimits.max_repay_income_ratio || surplusRatio < familyLimits.min_surplus_ratio || highInterestDebt > 0) {
            earnMinPct = 10;
            earnMaxPct = 30;
        } else if (cashCoverageMonths >= 12 && surplusRatio >= 0.25 && Number(riskToleranceCode) >= 30) {
            earnMinPct = 35;
            earnMaxPct = 65;
        }

        let preserveMinPct = 15;
        let preserveMaxPct = hasLargeExpense ? 60 : 50;
        if (num(fd['ast-house']) / baseAssets > 0.7) {
            preserveMaxPct = 65;
        }

        const classifyAmount = (value, minValue, maxValue, lowAdvice, highAdvice, okAdvice) => {
            if (value < minValue) return { status: '偏低', color: 'var(--accent-red)', advice: lowAdvice, isOk: false };
            if (value > maxValue) return { status: '偏高', color: 'var(--accent-orange)', advice: highAdvice, isOk: false };
            return { status: '合理', color: 'var(--accent-emerald)', advice: okAdvice, isOk: true };
        };

        const classifyPct = (value, minPct, maxPct, lowAdvice, highAdvice, okAdvice) => {
            const pct = value / baseAssets * 100;
            return classifyAmount(pct, minPct, maxPct, lowAdvice, highAdvice, okAdvice);
        };

        const spendStatus = classifyAmount(
            spendAmount, spendMin, spendMax,
            '近期生活费、月供和确定性开销储备不足，先补足独立现金账户。',
            '近期可花资金过厚，可把超出部分转入应急金或稳健增值资产。',
            '日常开销、月供和未来三年开销预留基本匹配。'
        );
        const lifeStatus = classifyAmount(
            lifeAmount, lifeMin, lifeMax + discountedInsuranceCashValue,
            '失业、医疗或家庭意外缓冲不足，优先补齐应急金、基础保障和高息债务处理。',
            '保命资金占用偏多，确认保障充足后可分批转入保值或生钱资产。',
            '风险兜底资金覆盖度较好，家庭抗冲击能力较稳。'
        );
        const earnStatus = classifyPct(
            earnAmount, earnMinPct, earnMaxPct,
            '生钱资产不足，长期购买力可能被通胀侵蚀。',
            '生钱资产偏高，若现金防线不足，回撤时可能被迫卖出。',
            '权益和经营类资产占比与当前风险承受力大致匹配。'
        );
        const preserveStatus = classifyPct(
            preserveAmount, preserveMinPct, preserveMaxPct,
            '保值稳健资产不足，组合对通胀和系统性波动的缓冲偏弱。',
            '保本升值资产偏重，尤其房产占比高时会压低流动性。',
            '稳健保值资产能够承担资产底仓和波动缓冲角色。'
        );

        const buckets = [
            {
                key: 'spend',
                title: '要花的钱',
                subtitle: '未来 2-12 个月刚性支出与确定性开销',
                amount: spendAmount,
                ratio: spendAmount / baseAssets,
                targetText: `${spendMinMonths}-${spendMaxMonths} 个月刚性支出，且覆盖未来12个月确定支出`,
                components: '活期现金、货币/短债中优先隔离的近期支出',
                ...spendStatus
            },
            {
                key: 'life',
                title: '保命的钱',
                subtitle: '失业、医疗、家庭意外与保障防线',
                amount: lifeAmount,
                ratio: lifeAmount / baseAssets,
                targetText: `${lifeMinMonths}-${lifeMaxMonths} 个月刚性支出 + 基础保障`,
                components: '应急现金、货币/短债、按流动性折扣计入的养老金/保险现金价值',
                ...lifeStatus
            },
            {
                key: 'earn',
                title: '生钱的钱',
                subtitle: '承担长期现金流与增长弹性的资产',
                amount: earnAmount,
                ratio: earnAmount / baseAssets,
                targetText: `${earnMinPct}-${earnMaxPct}% 总资产`,
                components: 'A股、港股、海外权益、其他可增值资产',
                ...earnStatus
            },
            {
                key: 'preserve',
                title: '保本升值的钱',
                subtitle: '稳健底仓、抗通胀与资产压舱石',
                amount: preserveAmount,
                ratio: preserveAmount / baseAssets,
                targetText: `${preserveMinPct}-${preserveMaxPct}% 总资产`,
                components: '房产、黄金、超额货币/短债留存',
                ...preserveStatus
            }
        ];

        const okCount = buckets.filter(item => item.isOk).length;
        const criticalLow = spendStatus.status === '偏低' || lifeStatus.status === '偏低';
        const score = Math.min(100, okCount * 22 + (criticalLow ? 0 : 12));
        let overallStatus = '结构需调整';
        let overallColor = 'var(--accent-orange)';
        if (okCount >= 3 && !criticalLow) {
            overallStatus = '配置较合理';
            overallColor = 'var(--accent-emerald)';
        } else if (criticalLow) {
            overallStatus = '基础防线不足';
            overallColor = 'var(--accent-red)';
        } else if (earnStatus.status === '偏高') {
            overallStatus = '收益资产偏激进';
            overallColor = 'var(--accent-orange)';
        }

        return {
            protectionAdequacyMonths,
            protectionGapMonths: Math.max(lifeMinMonths - protectionAdequacyMonths, 0),
            insuranceCashValue,
            insuranceLiquidityDiscount,
            overallStatus,
            overallColor,
            score,
            summary: `四类资金中 ${okCount}/4 项处于建议区间。先确保“要花的钱”和“保命的钱”不缺口，再讨论“生钱的钱”的进攻比例。`,
            buckets
        };
    },

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
        const familyLimits = planningRules.family_risk;
        const isLowCash = cashCoverageMonths < familyLimits.min_cash_coverage_months;
        const highInterestDebt = Number(fd['debt-high-interest']) || 0;
        const monthlyIncome = Number(fd['f-monthly-income']) || 0;
        const isHighDebt = leverage > familyLimits.max_leverage_ratio || repayIncomeRatio > familyLimits.max_repay_income_ratio || (monthlyIncome > 0 && highInterestDebt > monthlyIncome);
        const isLowSurplus = surplusRatio < familyLimits.min_surplus_ratio;

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
            isProhibitAggressive,
            fourMoney: this.calculateFourMoneyAnalysis(fd, totalAssets, netWorth, leverage, repayIncomeRatio, surplusRatio, cashCoverageMonths, riskToleranceCode)
        };
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = portfolioEngine;
} else {
    window.portfolioEngine = portfolioEngine;
}
