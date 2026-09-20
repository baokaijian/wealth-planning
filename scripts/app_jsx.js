function App() {
  const [state, setState] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        return migrateState(parsed);
      }
    } catch (e) {
      console.error('Failed to load state from localStorage:', e);
    }
    return INITIAL_STATE;
  });

  const [activeTab, setActiveTab] = useState('goals');
  const [editingGoal, setEditingGoal] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAssetModalOpen, setIsAssetModalOpen] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [showBehaviorBreakdown, setShowBehaviorBreakdown] = useState(false);
  const [showScoreBreakdown, setShowScoreBreakdown] = useState(false);
  const [showFullTimeline, setShowFullTimeline] = useState(false);
  const fileInputRef = useRef(null);

  const [newAsset, setNewAsset] = useState({
    code: '',
    name: '',
    type: 'ETF',
    weight: 5.0,
    yield: 3.5,
    market: 'A股',
    category: 'Equity',
    style: '红利低波',
    bucket: 'growth',
    targetIndexCode: 'H30269'
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      console.error('Failed to save state to localStorage:', e);
    }
  }, [state]);

  // 派生量化指标计算
  const boardMetrics = useMemo(() => calculateBoardMetrics(state.board), [state.board]);
  const bufferMetrics = useMemo(() => calculateBufferSimulation(state.board), [state.board]);
  const debtMetrics = useMemo(() => calculateDebtDecisionMetrics(state.debt, state.board.growthRate), [state.debt, state.board.growthRate]);
  const insuranceMetrics = useMemo(() => calculateInsuranceGap(state.health, state.insurance, debtMetrics.totalDebtBalance), [state.health, state.insurance, debtMetrics.totalDebtBalance]);
  const pensionMetrics = useMemo(() => calculatePensionTaxBenefit(state.pension), [state.pension]);
  const realEstateMetrics = useMemo(() => calculateRealEstateRisk(state.property, state.health, state.debt), [state.property, state.health, state.debt]);
  const liquidityMetrics = useMemo(() => checkLiquiditySegregation(state.health, state.board.principal), [state.health, state.board.principal]);
  const concentrationMetrics = useMemo(() => checkTripleConcentration(state.board.assets), [state.board.assets]);
  const behaviorMetrics = useMemo(() => calculateBehavioralEquityCeiling(state.behavior, state.board.assets), [state.behavior, state.board.assets]);
  
  // 温度计指标
  const activeThermometerIndex = useMemo(() => {
    const code = state.thermometer.selectedIndex || 'H30269';
    return THERMOMETER_INDICES.find(i => i.code === code) || THERMOMETER_INDICES[0];
  }, [state.thermometer.selectedIndex]);

  const activePercentile = useMemo(() => {
    if (state.thermometer.percentileOverrides && state.thermometer.percentileOverrides[activeThermometerIndex.code] !== undefined) {
      return state.thermometer.percentileOverrides[activeThermometerIndex.code];
    }
    return activeThermometerIndex.defaultPercentile || 50;
  }, [state.thermometer.percentileOverrides, activeThermometerIndex]);

  const thermometerMetrics = useMemo(() => calculateThermometerSignal(activePercentile), [activePercentile]);

  // 多目标资源挤占推演 (P1-5)
  const totalPrincipalYuan = (state.board.principal || 80) * 10000;
  const multiGoalResult = useMemo(() => {
    return calculateMultiGoalProjections(
      state.goals,
      totalPrincipalYuan,
      state.health.monthlySurplus || 12000,
      state.board.growthRate || 6.5,
      0.02
    );
  }, [state.goals, totalPrincipalYuan, state.health.monthlySurplus, state.board.growthRate]);

  const multiGoalProjections = useMemo(() => {
    return (multiGoalResult.goalResults || []).map(item => ({
      ...item,
      goal: item,
      allocatedMonthly: item.allocatedSurplus || 0,
      years: item.projection?.years || 1,
      months: item.projection?.months || 12,
      fvPrincipal: item.projection?.fvPrincipal || 0,
      fvMonthly: item.projection?.fvMonthly || 0,
      fvReserved: item.projection?.fvReserved || 0,
      fvTotal: item.projection?.fvTotal || 0,
      diff: item.projection?.diff || 0,
      isAchieved: item.projection?.isAchieved || false,
      gap: item.projection?.gap || 0,
      levers: item.projection?.levers || null
    }));
  }, [multiGoalResult]);

  // 资源池占用状态统计
  const poolStatus = useMemo(() => {
    let rigidPrincipalUsed = 0;
    let rigidMonthlyUsed = 0;
    let flexiblePrincipalUsed = 0;
    let flexibleMonthlyUsed = 0;

    multiGoalProjections.forEach(p => {
      if (p.priority === '刚性') {
        rigidPrincipalUsed += p.allocatedPrincipal;
        rigidMonthlyUsed += p.allocatedMonthly;
      } else {
        flexiblePrincipalUsed += p.allocatedPrincipal;
        flexibleMonthlyUsed += p.allocatedMonthly;
      }
    });

    const flexiblePrincipalAvailable = Math.max(0, totalPrincipalYuan - rigidPrincipalUsed);
    const flexibleMonthlyAvailable = Math.max(0, (state.health.monthlySurplus || 12000) - rigidMonthlyUsed);
    const remainingPrincipal = Math.max(0, flexiblePrincipalAvailable - flexiblePrincipalUsed);
    const remainingMonthly = Math.max(0, flexibleMonthlyAvailable - flexibleMonthlyUsed);

    return {
      rigidPrincipalUsed,
      rigidMonthlyUsed,
      flexiblePrincipalAvailable,
      flexibleMonthlyAvailable,
      remainingPrincipal,
      remainingMonthly
    };
  }, [multiGoalProjections, totalPrincipalYuan, state.health.monthlySurplus]);

  // 四大复合情景同时联测推演
  const replacementRate = state.stress.unemploymentReplacementRate ?? 0.3;
  const fourStressSimulations = useMemo(() => {
    const std = runCompoundStressTest(state.board, STRESS_PRESETS.standard, state.health, 36, replacementRate);
    const sev = runCompoundStressTest(state.board, STRESS_PRESETS.severe, state.health, 36, replacementRate);
    const stag = runCompoundStressTest(state.board, STRESS_PRESETS.stagflation, state.health, 36, replacementRate);
    const rep = HISTORICAL_REPLAYS[state.stress.selectedReplayId] || HISTORICAL_REPLAYS.replay_2018;
    const hist = runCompoundStressTest(state.board, {
      id: rep.id,
      name: rep.name,
      unemploymentMonths: 0,
      dividendDropRate: 1 - rep.dividendFactor,
      equityDrawdownRate: Math.abs(Math.min(...rep.monthlyDrawdown)),
      monthlyDrawdown: rep.monthlyDrawdown,
      medicalExpense: 0,
      delayMonths: 0,
      inflationRate: 0
    }, state.health, 36, replacementRate);

    // 寻找最严酷情景
    const simList = [
      { key: 'severe', name: '严重复合情景', sim: sev },
      { key: 'standard', name: '标准复合情景', sim: std },
      { key: 'stagflation', name: '滞胀情景', sim: stag },
      { key: 'replay', name: rep.name, sim: hist }
    ];

    simList.sort((a, b) => {
      if (a.sim.isExhausted && !b.sim.isExhausted) return -1;
      if (!a.sim.isExhausted && b.sim.isExhausted) return 1;
      if (a.sim.isExhausted && b.sim.isExhausted) {
        if (a.sim.exhaustionMonth !== b.sim.exhaustionMonth) return a.sim.exhaustionMonth - b.sim.exhaustionMonth;
        return b.sim.minAssetToSell - a.sim.minAssetToSell;
      }
      return a.sim.minBuffer - b.sim.minBuffer;
    });

    return {
      standard: std,
      severe: sev,
      stagflation: stag,
      replay: hist,
      worst: simList[0]
    };
  }, [state.board, state.health, replacementRate, state.stress.selectedReplayId]);

  // 当前激活展示的压力测试情景
  const currentStressScenario = useMemo(() => {
    if (state.stress.scenarioType === 'preset') {
      return STRESS_PRESETS[state.stress.selectedPresetId] || STRESS_PRESETS.standard;
    } else {
      const rep = HISTORICAL_REPLAYS[state.stress.selectedReplayId] || HISTORICAL_REPLAYS.replay_2018;
      return {
        id: rep.id,
        name: rep.name,
        description: rep.description,
        unemploymentMonths: 0,
        dividendDropRate: 1 - rep.dividendFactor,
        equityDrawdownRate: Math.abs(Math.min(...rep.monthlyDrawdown)),
        monthlyDrawdown: rep.monthlyDrawdown,
        medicalExpense: 0,
        medicalMonth: 0,
        delayMonths: 0,
        inflationRate: 0.0
      };
    }
  }, [state.stress]);

  const activeStressMetrics = useMemo(() => {
    return runCompoundStressTest(state.board, currentStressScenario, state.health, 36, replacementRate);
  }, [state.board, currentStressScenario, state.health, replacementRate]);

  // 增量资金再平衡计算
  const incrementalRebalance = useMemo(() => {
    return calculateIncrementalRebalance(
      state.board.assets,
      state.thermometer.userHoldings,
      state.thermometer.incrementalCapital || 50000
    );
  }, [state.board.assets, state.thermometer.userHoldings, state.thermometer.incrementalCapital]);

  const explainableScores = useMemo(() => calculateExplainableScores(state), [state]);
  const unifiedDashboard = useMemo(() => calculateUnifiedRiskDashboard(state), [state]);

  // 资产三桶统计
  const bucketSummary = useMemo(() => {
    let safety = 0;
    let growth = 0;
    let hedge = 0;
    Object.values(state.board.assets || {}).forEach(a => {
      const w = a.weight || 0;
      if (a.bucket === 'safety' || a.category === 'Cash') safety += w;
      else if (a.bucket === 'hedge' || a.category === 'Gold' || a.style === '利率长债') hedge += w;
      else growth += w;
    });
    return { safety, growth, hedge };
  }, [state.board.assets]);

  // 一键归一化权重至 100%
  const handleNormalizeWeights = () => {
    const assets = { ...state.board.assets };
    const keys = Object.keys(assets);
    if (keys.length === 0) return;
    const sum = Object.values(assets).reduce((acc, a) => acc + (Number(a.weight) || 0), 0);
    if (sum <= 0) return;
    let runningSum = 0;
    keys.forEach((code, idx) => {
      if (idx === keys.length - 1) {
        assets[code] = { ...assets[code], weight: Math.round((100.0 - runningSum) * 10) / 10 };
      } else {
        const normalized = Math.round(((assets[code].weight || 0) / sum) * 1000) / 10;
        assets[code] = { ...assets[code], weight: normalized };
        runningSum += normalized;
      }
    });
    setState(prev => ({
      ...prev,
      board: { ...prev.board, assets }
    }));
  };

  // 导出 JSON
  const handleExportJSON = () => {
    const jsonStr = JSON.stringify(state, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `wealth_planning_backup_${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
  };

  // 导入 JSON
  const handleImportJSON = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target.result);
        const migrated = migrateState(parsed);
        setState(migrated);
        alert('配置已成功自本地文件恢复！');
      } catch (err) {
        alert('导入失败：文件不是合法的 JSON 数据！');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  // 保存快照
  const handleSaveSnapshot = () => {
    try {
      const snapsRaw = localStorage.getItem('WEALTH_PLANNING_SNAPSHOTS_V1') || '[]';
      const snaps = JSON.parse(snapsRaw);
      snaps.unshift({
        timestamp: new Date().toISOString(),
        label: `快照 ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}`,
        state
      });
      localStorage.setItem('WEALTH_PLANNING_SNAPSHOTS_V1', JSON.stringify(snaps.slice(0, 10)));
      alert('历史快照已保存在本地浏览器！');
    } catch (err) {
      console.error(err);
    }
  };

  // 重置数据
  const handleResetAll = () => {
    if (window.confirm("确定要重置所有财务数据并恢复系统演示初始配置吗？此操作无法撤销。")) {
      localStorage.removeItem(STORAGE_KEY);
      setState(INITIAL_STATE);
    }
  };

  // 快速载入验收示例
  const handleLoadAcceptanceGoal = () => {
    const newGoal = {
      id: 'goal-edu-' + Date.now(),
      name: '2035 年子女教育金 (验收示例)',
      type: '子女教育金',
      targetAmount: 1000000,
      targetYear: 2035,
      priority: '刚性',
      reservedAmount: 0,
      linkTo1To3y: false,
      retireConfig: { currentAge: 35, retireAge: 50, retireMonthlyExpense: 10000 }
    };
    setState({
      ...state,
      goals: [newGoal, ...state.goals]
    });
    setActiveTab('goals');
  };

  // 风险卡片跳转
  const handleJumpToModule = (tab, anchorId) => {
    setActiveTab(tab);
    setTimeout(() => {
      const el = document.getElementById(anchorId);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  // 目标操作
  const handleOpenCreate = () => {
    setEditingGoal({
      id: 'goal-' + Date.now(),
      name: '',
      type: '子女教育金',
      targetAmount: 500000,
      targetYear: 2035,
      priority: '刚性',
      reservedAmount: 0,
      linkTo1To3y: false,
      retireConfig: { currentAge: 35, retireAge: 50, retireMonthlyExpense: 10000 }
    });
    setIsModalOpen(true);
  };

  const handleOpenEdit = (goal) => {
    setEditingGoal({ ...goal });
    setIsModalOpen(true);
  };

  const handleDeleteGoal = (id) => {
    if (window.confirm("确定删除该规划目标吗？")) {
      setState({
        ...state,
        goals: state.goals.filter(g => g.id !== id)
      });
    }
  };

  const handleSaveGoal = (e) => {
    e.preventDefault();
    if (!editingGoal.name.trim()) {
      alert("请输入目标名称！");
      return;
    }
    const exists = state.goals.some(g => g.id === editingGoal.id);
    if (exists) {
      setState({
        ...state,
        goals: state.goals.map(g => g.id === editingGoal.id ? editingGoal : g)
      });
    } else {
      setState({
        ...state,
        goals: [editingGoal, ...state.goals]
      });
    }
    setIsModalOpen(false);
  };

  // 资产标的操作
  const handleAddAsset = (e) => {
    e.preventDefault();
    if (!newAsset.code.trim() || !newAsset.name.trim()) {
      alert("请输入资产代码与名称！");
      return;
    }
    setState(prev => ({
      ...prev,
      board: {
        ...prev.board,
        assets: {
          ...prev.board.assets,
          [newAsset.code.trim()]: {
            name: newAsset.name.trim(),
            type: newAsset.type,
            weight: Number(newAsset.weight) || 0,
            yield: Number(newAsset.yield) || 0,
            months: { 6: 0.5, 12: 0.5 },
            market: newAsset.market,
            category: newAsset.category,
            style: newAsset.style,
            bucket: newAsset.bucket,
            targetIndexCode: newAsset.targetIndexCode || 'H30269'
          }
        }
      }
    }));
    setIsAssetModalOpen(false);
    setNewAsset({
      code: '',
      name: '',
      type: 'ETF',
      weight: 5.0,
      yield: 3.5,
      market: 'A股',
      category: 'Equity',
      style: '红利低波',
      bucket: 'growth',
      targetIndexCode: 'H30269'
    });
  };

  const handleDeleteAsset = (code) => {
    if (window.confirm(`确定从配置池中移除资产 [${code}] 吗？`)) {
      setState(prev => {
        const nextAssets = { ...prev.board.assets };
        delete nextAssets[code];
        return {
          ...prev,
          board: { ...prev.board, assets: nextAssets }
        };
      });
    }
  };

  return (
    <div>
      {/* 顶部导航 */}
      <header>
        <div className="header-inner">
          <div className="logo-area">
            <div className="logo-badge">🛡️</div>
            <div>
              <div className="brand-title">家庭财富规划与量化风险管理系统</div>
              <div className="brand-subtitle">流动性硬隔离 · 保障缺口 · 行为约束 · 复合情景压力测试</div>
            </div>
          </div>

          <div className="nav-tabs">
            <button className={`nav-tab-btn ${activeTab === 'goals' ? 'active' : ''}`} onClick={() => setActiveTab('goals')}>
              🎯 目标规划 <span className="tag tag-blue" style={{ marginLeft: 4 }}>{state.goals.length}</span>
            </button>
            <button className={`nav-tab-btn ${activeTab === 'board' ? 'active' : ''}`} onClick={() => setActiveTab('board')}>
              📊 资产看板
            </button>
            <button className={`nav-tab-btn ${activeTab === 'health' ? 'active' : ''}`} onClick={() => setActiveTab('health')}>
              🩺 资产体检与保障
            </button>
            <button className={`nav-tab-btn ${activeTab === 'buffer' ? 'active' : ''}`} onClick={() => setActiveTab('buffer')}>
              ⏱️ 缓冲池与压力测试
            </button>
            <button className={`nav-tab-btn ${activeTab === 'thermometer' ? 'active' : ''}`} onClick={() => setActiveTab('thermometer')}>
              🌡️ 估值温度计与再平衡
            </button>
            <button className={`nav-tab-btn ${activeTab === 'report' ? 'active' : ''}`} onClick={() => setActiveTab('report')}>
              📋 体检报告导出
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="storage-tag" title="所有家庭财务数据完全保存在您的本地浏览器 localStorage 中，不向任何第三方服务器发送">
              <span className="pulse-dot"></span>
              纯本地存储
            </div>
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept=".json" 
              onChange={handleImportJSON} 
            />
            <button className="btn btn-outline btn-sm" onClick={handleExportJSON} title="导出本地 JSON 备份文件">
              📥 导出
            </button>
            <button className="btn btn-outline btn-sm" onClick={() => fileInputRef.current && fileInputRef.current.click()} title="从本地 JSON 导入">
              📤 导入
            </button>
            <button className="btn btn-outline btn-sm" onClick={handleSaveSnapshot} title="保存当前快照到本地历史">
              📸 快照
            </button>
            <button className="btn btn-outline btn-sm" onClick={handleResetAll} title="重置回初始示范数据">
              🔄 重置
            </button>
          </div>
        </div>
      </header>

      {/* P0-6: 资产配置权重总和异常置顶报警条 */}
      {!boardMetrics.isWeightValid && (
        <div style={{
          background: 'rgba(234, 88, 12, 0.95)',
          color: '#FFF',
          padding: '10px 20px',
          fontWeight: 600,
          fontSize: '0.86rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 4px 15px rgba(234, 88, 12, 0.4)',
          position: 'sticky',
          top: '65px',
          zIndex: 95
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.2rem' }}>⚠️</span>
            <span>
              <strong>【资产配置权重异常】</strong>当前资产配置总权重为 <strong>{boardMetrics.totalWeight.toFixed(1)}%</strong>（标准配置需严格等于 100.0%）！当前误差可能导致收益率与现金流测算偏离。
            </span>
          </div>
          <button 
            className="btn btn-sm" 
            style={{ background: '#FFF', color: '#C2410C', fontWeight: 700 }}
            onClick={handleNormalizeWeights}
          >
            一键归一化至 100%
          </button>
        </div>
      )}

      {/* 流动性硬隔离超限警告条 (持久置顶) */}
      {liquidityMetrics.isViolated && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.92)',
          color: '#FFF',
          padding: '10px 20px',
          fontWeight: 600,
          fontSize: '0.86rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 4px 15px rgba(239, 68, 68, 0.4)',
          position: 'sticky',
          top: !boardMetrics.isWeightValid ? '110px' : '65px',
          zIndex: 90
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.2rem' }}>🚨</span>
            <span>
              <strong>【流动性硬隔离严重超限】</strong>当前可用投资本金 ¥{(state.board.principal * 10000).toLocaleString()} 元，超出安全可投资上限 (¥{Math.round(liquidityMetrics.investableCeiling).toLocaleString()} 元) 达 ¥{Math.round(liquidityMetrics.excessAmount).toLocaleString()} 元！<strong>{liquidityMetrics.warningText}</strong>
            </span>
          </div>
          <button 
            className="btn btn-sm" 
            style={{ background: '#FFF', color: '#B91C1C', fontWeight: 700 }}
            onClick={() => setState({ ...state, board: { ...state.board, principal: Math.max(0, Math.floor(liquidityMetrics.investableCeiling / 10000)) } })}
          >
            一键调减本金至安全线
          </button>
        </div>
      )}

      <main className="container">
        {/* TAB 1: 🎯 目标导向规划 (含多目标资源挤占模型 P1-5) */}
        {activeTab === 'goals' && (
          <div>
            {/* 资源池占用与挤占状态栏 */}
            <div style={{ background: 'rgba(30, 41, 59, 0.7)', border: '1px solid var(--card-border)', borderRadius: '12px', padding: '16px 20px', marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38BDF8' }}>
                  🌊 多目标资源挤占池状态（刚性目标优先占用，弹性目标递减分配）
                </div>
                <div style={{ fontSize: '0.78rem', color: '#94A3B8' }}>
                  口径：刚性目标享有可用本金与月结余的第一顺位优先权
                </div>
              </div>
              <div className="grid-2" style={{ gap: '14px' }}>
                <div style={{ background: 'rgba(0,0,0,0.25)', padding: '12px 14px', borderRadius: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '6px' }}>
                    <span>可用总本金池：<strong>¥{totalPrincipalYuan.toLocaleString()} 元</strong></span>
                    <span style={{ color: poolStatus.remainingPrincipal > 0 ? '#34D399' : '#FBBF24' }}>
                      剩余未分配: ¥{Math.round(poolStatus.remainingPrincipal).toLocaleString()} 元
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#CBD5E1' }}>
                    🔴 刚性目标占用: <strong>¥{Math.round(poolStatus.rigidPrincipalUsed).toLocaleString()}</strong> | 🔵 弹性目标可用: <strong>¥{Math.round(poolStatus.flexiblePrincipalAvailable).toLocaleString()}</strong>
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.25)', padding: '12px 14px', borderRadius: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '6px' }}>
                    <span>每月可结余定投池：<strong>¥{Number(state.health.monthlySurplus).toLocaleString()} 元/月</strong></span>
                    <span style={{ color: poolStatus.remainingMonthly > 0 ? '#34D399' : '#FBBF24' }}>
                      剩余未分配: ¥{Math.round(poolStatus.remainingMonthly).toLocaleString()} 元/月
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#CBD5E1' }}>
                    🔴 刚性目标占用: <strong>¥{Math.round(poolStatus.rigidMonthlyUsed).toLocaleString()}</strong>/月 | 🔵 弹性目标可用: <strong>¥{Math.round(poolStatus.flexibleMonthlyAvailable).toLocaleString()}</strong>/月
                  </div>
                </div>
              </div>
            </div>

            <div className="grid-4" style={{ marginBottom: '20px' }}>
              <div className="metric-card">
                <div className="metric-label">规划目标总数</div>
                <div className="metric-val">{state.goals.length} <span style={{ fontSize: '1rem', color: '#94A3B8' }}>个</span></div>
                <div className="metric-sub">
                  <span style={{ color: '#34D399' }}>{multiGoalProjections.filter(p => p.isAchieved).length} 已达成</span> · 
                  <span style={{ color: '#FB7185', marginLeft: '4px' }}>{multiGoalProjections.filter(p => !p.isAchieved).length} 待弥补</span>
                </div>
              </div>
              <div className="metric-card">
                <div className="metric-label">月可结余 (体检输入)</div>
                <div className="metric-val" style={{ color: '#38BDF8' }}>¥{Number(state.health.monthlySurplus).toLocaleString()}</div>
                <div className="metric-sub">看板长期增长预期: {state.board.growthRate}%</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">目标资金需求总额</div>
                <div className="metric-val">
                  ¥{(state.goals.reduce((acc, g) => acc + (Number(g.targetAmount) || 0), 0) / 10000).toFixed(0)} <span style={{ fontSize: '1rem', color: '#94A3B8' }}>万</span>
                </div>
                <div className="metric-sub">名义金额需求加总</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">推演终值总和 (挤占后)</div>
                <div className="metric-val" style={{ color: '#10B981' }}>
                  ¥{(multiGoalProjections.reduce((acc, p) => acc + p.fvTotal, 0) / 10000).toFixed(0)} <span style={{ fontSize: '1rem', color: '#94A3B8' }}>万</span>
                </div>
                <div className="metric-sub">按资源分配真实复利终值加总</div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ fontSize: '1.05rem', fontWeight: 600 }}>目标列表 ({state.goals.length})</div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button className="btn btn-outline" onClick={handleLoadAcceptanceGoal}>
                  ⚡ 快速载入验收示例 (2035 子女教育金 100 万)
                </button>
                <button className="btn btn-primary" onClick={handleOpenCreate}>
                  ➕ 新增规划目标
                </button>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '16px' }}>
              {multiGoalProjections.map(proj => {
                const goal = proj.goal;
                const isFire = goal.type === '提前退休';
                let fireSim = null;
                if (isFire) {
                  const retCfg = goal.retireConfig || { currentAge: 35, retireAge: 50, retireMonthlyExpense: 12000 };
                  fireSim = simulateEarlyRetirement({
                    currentAge: retCfg.currentAge,
                    retireAge: retCfg.retireAge,
                    targetAmount: goal.targetAmount,
                    projectedCapitalAtRetire: proj.fvTotal,
                    monthlyExpense: retCfg.retireMonthlyExpense,
                    dividendYield: boardMetrics.blendedYield,
                    bufferInterestRate: state.board.moneyMarketRate,
                    endAge: 85
                  });
                }

                return (
                  <div key={goal.id} className="card" style={{ marginBottom: '0', border: proj.isAchieved ? '1px solid rgba(16, 185, 129, 0.35)' : '1px solid rgba(244, 63, 94, 0.35)' }}>
                    <div className="card-header" style={{ marginBottom: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontSize: '1.3rem' }}>
                          {goal.type === '子女教育金' ? '🎓' : (goal.type === '养老储备' ? '👵' : (goal.type === '买房首付' ? '🏠' : (goal.type === '提前退休' ? '🌴' : '🎯')))}
                        </span>
                        <div>
                          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#FFF' }}>{goal.name}</div>
                          <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                            <span className="tag tag-blue">{goal.type}</span>
                            <span className={`tag ${goal.priority === '刚性' ? 'tag-red' : 'tag-green'}`}>
                              {goal.priority === '刚性' ? '🔴 刚性优先级 (优先分配资源)' : '🔵 弹性优先级 (递减分配)'}
                            </span>
                            <span className="tag" style={{ background: 'rgba(255,255,255,0.06)' }}>目标时点: {goal.targetYear} 年 (还剩 {proj.years} 年)</span>
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span className={`tag ${proj.isAchieved ? 'tag-green' : 'tag-red'}`} style={{ fontSize: '0.85rem', padding: '4px 10px' }}>
                          {proj.isAchieved ? `🟢 预计富余 ¥${Math.round(proj.diff).toLocaleString()} 元` : `🔴 预计缺口 ¥${Math.round(proj.gap).toLocaleString()} 元`}
                        </span>
                        <button className="btn btn-outline btn-sm" onClick={() => handleOpenEdit(goal)}>✏️ 编辑</button>
                        <button className="btn btn-danger btn-sm" onClick={() => handleDeleteGoal(goal.id)}>🗑️ 删除</button>
                      </div>
                    </div>

                    {/* 指标卡片 */}
                    <div className="grid-4" style={{ marginBottom: '14px' }}>
                      <div className="metric-card">
                        <div className="metric-label">目标设定金额</div>
                        <div className="metric-val">¥{Number(goal.targetAmount).toLocaleString()}</div>
                        <div className="metric-sub">时点: {goal.targetYear} 年底</div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">分配资源终值 (FV)</div>
                        <div className="metric-val" style={{ color: proj.isAchieved ? '#10B981' : '#FBBF24' }}>
                          ¥{Math.round(proj.fvTotal).toLocaleString()}
                        </div>
                        <div className="metric-sub">本金终值+月投终值+预留终值</div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">分配本金贡献</div>
                        <div className="metric-val" style={{ fontSize: '1.15rem' }}>¥{Math.round(proj.fvPrincipal).toLocaleString()}</div>
                        <div className="metric-sub">获分配本金 ¥{Math.round(proj.allocatedPrincipal).toLocaleString()}</div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">分配月定投贡献</div>
                        <div className="metric-val" style={{ fontSize: '1.15rem', color: '#38BDF8' }}>¥{Math.round(proj.fvMonthly).toLocaleString()}</div>
                        <div className="metric-sub">获分配月结余 ¥{Math.round(proj.allocatedMonthly).toLocaleString()}/月</div>
                      </div>
                    </div>

                    {/* 缺口三大杠杆反解 */}
                    {!proj.isAchieved && proj.levers && (
                      <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '10px', padding: '14px', marginBottom: '12px' }}>
                        <div style={{ fontWeight: 700, color: '#F87171', marginBottom: '8px', fontSize: '0.9rem' }}>
                          ⚖️ 缺口调控方案（三大可调杠杆反解测算）：
                        </div>
                        <div className="grid-3">
                          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px' }}>
                            <div style={{ fontSize: '0.8rem', color: '#CBD5E1', fontWeight: 600 }}>杠杆 1：储蓄端 (开源节流)</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#FBBF24', margin: '4px 0' }}>
                              每月需多储蓄 ¥{proj.levers.extraMonthly.toLocaleString()} 元
                            </div>
                            <div style={{ fontSize: '0.72rem', color: '#94A3B8' }}>
                              若月结余增加至 ¥{(proj.allocatedMonthly + proj.levers.extraMonthly).toLocaleString()} 元可自然弥合
                            </div>
                          </div>

                          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px' }}>
                            <div style={{ fontSize: '0.8rem', color: '#CBD5E1', fontWeight: 600 }}>杠杆 2：收益端 (组合提效)</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: proj.levers.isRateSafe ? '#10B981' : '#F87171', margin: '4px 0' }}>
                              收益率需提至 {proj.levers.reqRatePct}% (+{proj.levers.rateDiffPct}%)
                            </div>
                            <div style={{ fontSize: '0.72rem', color: proj.levers.isRateSafe ? '#34D399' : '#F87171' }}>
                              {proj.levers.isRateSafe ? '✅ 仍处于稳健理财合理区间 (≤8%)' : '⚠️ 超过稳健上限 8%，存在本金波动风险，不建议盲目博取'}
                            </div>
                          </div>

                          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px' }}>
                            <div style={{ fontSize: '0.8rem', color: '#CBD5E1', fontWeight: 600 }}>杠杆 3：目标端 (放宽诉求)</div>
                            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38BDF8', margin: '4px 0' }}>
                              调减至 ¥{(goal.targetAmount - proj.levers.loosenAmount).toLocaleString()} 元
                            </div>
                            <div style={{ fontSize: '0.72rem', color: '#94A3B8' }}>
                              或时点延后 {proj.levers.delayYears} 年至 {proj.levers.delayedTargetYear} 年自然达成
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 提前退休持久性检验 */}
                    {isFire && fireSim && (
                      <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: '10px', padding: '14px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <div style={{ fontWeight: 700, color: '#38BDF8', fontSize: '0.9rem' }}>
                            🌴 提前退休模式：85 岁全生命周期持久性检验 (分红支取与本金平滑)
                          </div>
                          <span className={`tag ${fireSim.isSustainable ? 'tag-green' : 'tag-red'}`}>
                            {fireSim.isSustainable ? '✅ 资本永续至85岁 (未耗尽)' : `⚠️ 资产在 ${fireSim.depletionAge} 岁将耗尽`}
                          </span>
                        </div>
                        <div className="grid-3" style={{ fontSize: '0.8rem' }}>
                          <div>退休期初推演本金: <strong>¥{Math.round(proj.fvTotal).toLocaleString()}</strong></div>
                          <div>退休后月生活费: <strong>¥{Number(goal.retireConfig?.retireMonthlyExpense || 12000).toLocaleString()}/月</strong></div>
                          <div>
                            最脆弱月份: <strong>第 {fireSim.mostFragileMonth} 个月</strong> (约 {fireSim.mostFragileAge} 岁, 水位: ¥{Math.round(fireSim.lowestCapital).toLocaleString()})
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 2: 📊 资产配置与股息看板 (含3桶结构 P0-4 & 归一化 P0-6) */}
        {activeTab === 'board' && (
          <div>
            {/* 保障缺口警告条 */}
            {insuranceMetrics.shouldWarnAndDowngrade && (
              <div style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: '2px solid #EF4444',
                borderRadius: '10px',
                padding: '14px 18px',
                marginBottom: '20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: '28px' }}>🛡️</span>
                  <div>
                    <div style={{ color: '#F87171', fontWeight: 700, fontSize: '0.95rem' }}>
                      先补保障再配置：当前家庭抗风险兜底严重不足！
                    </div>
                    <div style={{ color: '#FECACA', fontSize: '0.82rem' }}>
                      保障自评为“{insuranceMetrics.coverageTier === 'none' ? '极低/空白' : '基础不足'}”，存在寿险/重疾净缺口且缺少百万医疗大额兜底。<strong>当前资产配置结论降级为【参考值】</strong>！
                    </div>
                  </div>
                </div>
                <button className="btn btn-danger btn-sm" onClick={() => handleJumpToModule('health', 'insurance-gap-card')}>
                  去补齐保障
                </button>
              </div>
            )}

            {/* 3桶资产配置概览条 */}
            <div className="card" style={{ padding: '16px 20px', marginBottom: '18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div className="card-title" style={{ fontSize: '1rem' }}>
                  <span>🧱 科学三桶资产配置结构总览</span>
                  <span className="tag tag-blue">标准锚定：安全30% / 成长55% / 对冲15%</span>
                </div>
                <button className="btn btn-outline btn-sm" onClick={() => setIsAssetModalOpen(true)}>
                  ➕ 添加自定义标的
                </button>
              </div>

              <div className="grid-3" style={{ gap: '14px' }}>
                <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '8px', padding: '12px' }}>
                  <div style={{ fontSize: '0.8rem', color: '#94A3B8' }}>安全防御桶 (现金货币 + 短融债)</div>
                  <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#34D399', margin: '2px 0' }}>
                    {bucketSummary.safety.toFixed(1)}% <span style={{ fontSize: '0.85rem', color: '#94A3B8' }}>(目标 30%)</span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#CBD5E1' }}>提供绝对流动性与基底防御</div>
                </div>

                <div style={{ background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: '8px', padding: '12px' }}>
                  <div style={{ fontSize: '0.8rem', color: '#94A3B8' }}>长期成长桶 (红利低波 + 核心宽基)</div>
                  <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#38BDF8', margin: '2px 0' }}>
                    {bucketSummary.growth.toFixed(1)}% <span style={{ fontSize: '0.85rem', color: '#94A3B8' }}>(目标 55%)</span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#CBD5E1' }}>现金分红引擎与长期购买力增值</div>
                </div>

                <div style={{ background: 'rgba(168, 85, 247, 0.1)', border: '1px solid rgba(168, 85, 247, 0.25)', borderRadius: '8px', padding: '12px' }}>
                  <div style={{ fontSize: '0.8rem', color: '#94A3B8' }}>综合对冲桶 (黄金ETF + 长端国债)</div>
                  <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#C084FC', margin: '2px 0' }}>
                    {bucketSummary.hedge.toFixed(1)}% <span style={{ fontSize: '0.85rem', color: '#94A3B8' }}>(目标 15%)</span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#CBD5E1' }}>抵御黑天鹅事件与通胀通缩异动</div>
                </div>
              </div>
            </div>

            {/* 1. 流动性硬隔离控制卡片 */}
            <div className="card" id="liquidity-isolation-card" style={{ border: liquidityMetrics.isViolated ? '2px solid #EF4444' : '1px solid var(--card-border)' }}>
              <div className="card-header">
                <div className="card-title">
                  <span>💧 流动性硬隔离校验：防止投资本金侵入短期确定性刚需</span>
                  <span className={`tag ${liquidityMetrics.isViolated ? 'tag-red' : 'tag-green'}`}>
                    {liquidityMetrics.isViolated ? '⚠️ 超限预警' : '✅ 安全合规'}
                  </span>
                </div>
                <span style={{ fontSize: '0.78rem', color: '#94A3B8' }}>
                  短期支出覆盖倍数: <strong style={{ color: liquidityMetrics.isCoverageInsufficient ? '#F87171' : '#34D399' }}>{liquidityMetrics.coverageRatio}x</strong> (安全底线 1.5x)
                </span>
              </div>

              <div className="grid-4" style={{ marginBottom: '16px' }}>
                <div className="metric-card">
                  <div className="metric-label">流动金融资产总额</div>
                  <div className="metric-val">¥{liquidityMetrics.liquidFinancialAssets.toLocaleString()}</div>
                  <div className="metric-sub">活期+短债+基金+黄金等 (不含房产)</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">12个月确定性支出 (100%隔离)</div>
                  <div className="metric-val" style={{ color: '#FBBF24' }}>¥{liquidityMetrics.bucket1y.toLocaleString()}</div>
                  <div className="metric-sub">未来1年绝对刚需，禁止投资博取</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">1-3年确定支出 (50%折减)</div>
                  <div className="metric-val" style={{ color: '#38BDF8' }}>¥{(liquidityMetrics.bucket1To3y * liquidityMetrics.discountFactor).toLocaleString()}</div>
                  <div className="metric-sub">¥{liquidityMetrics.bucket1To3y.toLocaleString()} × 折减系数 50%</div>
                </div>
                <div className="metric-card" style={{ background: liquidityMetrics.isViolated ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)' }}>
                  <div className="metric-label">可投资资金上限</div>
                  <div className="metric-val" style={{ color: liquidityMetrics.isViolated ? '#F87171' : '#10B981' }}>
                    ¥{Math.round(liquidityMetrics.investableCeiling).toLocaleString()}
                  </div>
                  <div className="metric-sub">
                    {liquidityMetrics.isViolated ? `已超限 ¥${Math.round(liquidityMetrics.excessAmount).toLocaleString()} 元！` : '可用本金安全上限'}
                  </div>
                </div>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: '8px', fontSize: '0.82rem', color: '#CBD5E1', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  💡 <strong>职责辨析</strong>：{liquidityMetrics.distinctionNote}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <label style={{ fontSize: '0.8rem', color: '#94A3B8' }}>总可用本金 (万元):</label>
                  <input 
                    type="number" 
                    className={`input-control ${liquidityMetrics.isViolated ? 'error' : ''}`}
                    style={{ width: '110px', padding: '4px 8px' }}
                    value={state.board.principal}
                    step="5"
                    onChange={e => setState({ ...state, board: { ...state.board, principal: parseFloat(e.target.value) || 0 } })}
                  />
                </div>
              </div>
            </div>

            {/* 2. 行为约束引擎卡片 (P0-4 严格 Equity 口径) */}
            <div className="card" id="behavior-constraint-card" style={{ border: behaviorMetrics.isExceeded ? '2px solid #EF4444' : '1px solid var(--card-border)' }}>
              <div className="card-header">
                <div className="card-title">
                  <span>🧠 行为约束引擎：自评心理承受转化为持仓硬约束</span>
                  <span className={`tag ${behaviorMetrics.isExceeded ? 'tag-red' : 'tag-green'}`}>
                    {behaviorMetrics.isExceeded ? '⚠️ 实际持仓超限' : '✅ 符合心理耐受'}
                  </span>
                </div>
                <button className="btn btn-outline btn-sm" onClick={() => setShowBehaviorBreakdown(!showBehaviorBreakdown)}>
                  {showBehaviorBreakdown ? '收起扣减明细' : '为什么是这个数？'}
                </button>
              </div>

              <div className="grid-3" style={{ marginBottom: '14px' }}>
                <div className="metric-card">
                  <div className="metric-label">您的行为约束权益上限</div>
                  <div className="metric-val" style={{ color: '#10B981' }}>{behaviorMetrics.finalCeiling}%</div>
                  <div className="metric-sub">自评回撤 {behaviorMetrics.bracket} 经行为扣减后底线</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">当前组合严格权益占比</div>
                  <div className="metric-val" style={{ color: behaviorMetrics.isExceeded ? '#F87171' : '#38BDF8' }}>
                    {behaviorMetrics.actualEquityWeight.toFixed(1)}%
                  </div>
                  <div className="metric-sub">
                    {behaviorMetrics.isExceeded ? `超出行为约束 ${behaviorMetrics.excessWeight.toFixed(1)}%！` : '处于合规安全水位'}
                  </div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">隐含极端权益回撤承受力</div>
                  <div className="metric-val" style={{ color: '#FBBF24' }}>约 {behaviorMetrics.implicitDrawdown}%</div>
                  <div className="metric-sub">上限 × 历史极端权益回撤 (40%)</div>
                </div>
              </div>

              {/* 行为微调表单 */}
              <div className="grid-4" style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', marginBottom: '12px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">自评最大承受回撤</label>
                  <select 
                    className="input-control"
                    value={state.behavior.drawdownBracket}
                    onChange={e => setState({ ...state, behavior: { ...state.behavior, drawdownBracket: e.target.value } })}
                  >
                    {Object.keys(BEHAVIOR_DRAWDOWN_MAP).map(k => <option key={k} value={k}>{k}</option>)}
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">大跌第一反应</label>
                  <select 
                    className="input-control"
                    value={state.behavior.marketDropReaction}
                    onChange={e => setState({ ...state, behavior: { ...state.behavior, marketDropReaction: e.target.value } })}
                  >
                    <option value="panic_sell">恐慌卖出 (-15%)</option>
                    <option value="pause_watch">暂停观望 (-5%)</option>
                    <option value="buy_more">逆势加仓 (0%)</option>
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">生活费高度依赖投资现金流</label>
                  <select 
                    className="input-control"
                    value={state.behavior.cashflowRelianceHigh ? 'yes' : 'no'}
                    onChange={e => setState({ ...state, behavior: { ...state.behavior, cashflowRelianceHigh: e.target.value === 'yes' } })}
                  >
                    <option value="yes">是 (扣减10%)</option>
                    <option value="no">否 (有稳定职业收入)</option>
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">行业波动大且失业恢复>6月</label>
                  <select 
                    className="input-control"
                    value={state.behavior.industryVolatileHigh ? 'yes' : 'no'}
                    onChange={e => setState({ ...state, behavior: { ...state.behavior, industryVolatileHigh: e.target.value === 'yes' } })}
                  >
                    <option value="yes">是 (扣减10%)</option>
                    <option value="no">否 (收入连续性强)</option>
                  </select>
                </div>
              </div>

              {showBehaviorBreakdown && (
                <div style={{ background: 'rgba(255,255,255,0.04)', padding: '12px', borderRadius: '8px', fontSize: '0.8rem', color: '#CBD5E1' }}>
                  <div style={{ fontWeight: 600, marginBottom: '6px', color: '#38BDF8' }}>📋 透明化扣减过程：</div>
                  {behaviorMetrics.breakdownList.map((item, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                      <span>{item.label}</span>
                      <strong style={{ color: item.delta.startsWith('-') ? '#F87171' : '#34D399' }}>{item.delta}</strong>
                    </div>
                  ))}
                  <div style={{ marginTop: '6px', color: '#94A3B8', fontSize: '0.72rem' }}>
                    *注：仅对 category === 'Equity' 的资产严格统计为权益仓位，保底 15% 为系统安全底线。
                  </div>
                </div>
              )}
            </div>

            {/* 3. 三重集中度检查与资产明细表 */}
            <div className="card" id="concentration-card">
              <div className="card-header">
                <div className="card-title">
                  <span>🎯 资产池明细与三重集中度监控</span>
                  <span className={`tag ${boardMetrics.isWeightValid ? 'tag-green' : 'tag-red'}`}>
                    总权重: {boardMetrics.totalWeight.toFixed(1)}% {boardMetrics.isWeightValid ? '(达标)' : '(需调至100%)'}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {!boardMetrics.isWeightValid && (
                    <button className="btn btn-outline btn-sm" onClick={handleNormalizeWeights}>
                      ⚡ 归一化至100%
                    </button>
                  )}
                  <button className="btn btn-primary btn-sm" onClick={() => setIsAssetModalOpen(true)}>
                    ➕ 添加资产
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '18px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', borderLeft: `4px solid ${concentrationMetrics.targetStatus === 'red' ? '#EF4444' : (concentrationMetrics.targetStatus === 'yellow' ? '#F59E0B' : '#10B981')}` }}>
                  <div>
                    <strong>1. 标的集中度</strong>：单一最大【{concentrationMetrics.maxSingle.name}】占比 {concentrationMetrics.maxSingle.weight.toFixed(1)}%，前三标的合计 {concentrationMetrics.top3Weight.toFixed(1)}%
                  </div>
                  <span className={`tag ${concentrationMetrics.targetStatus === 'red' ? 'tag-red' : (concentrationMetrics.targetStatus === 'yellow' ? 'tag-yellow' : 'tag-green')}`}>
                    {concentrationMetrics.targetAdvice}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', borderLeft: `4px solid ${concentrationMetrics.marketStatus === 'yellow' ? '#F59E0B' : '#10B981'}` }}>
                  <div>
                    <strong>2. 市场与币种集中度</strong>：最大板块【{concentrationMetrics.maxMarket.market}】占比 {concentrationMetrics.maxMarket.weight.toFixed(1)}%
                  </div>
                  <span className={`tag ${concentrationMetrics.marketStatus === 'yellow' ? 'tag-yellow' : 'tag-green'}`}>
                    {concentrationMetrics.marketAdvice}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', borderLeft: `4px solid ${concentrationMetrics.styleStatus === 'yellow' ? '#F59E0B' : '#10B981'}` }}>
                  <div>
                    <strong>3. 策略风格集中度</strong>：红利低波类标的权重合计达 {concentrationMetrics.dividendStyleWeight.toFixed(1)}%
                  </div>
                  <span className={`tag ${concentrationMetrics.styleStatus === 'yellow' ? 'tag-yellow' : 'tag-green'}`}>
                    {concentrationMetrics.styleAdvice}
                  </span>
                </div>
              </div>

              {/* 资产列表 */}
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>代码</th>
                      <th>资产名称</th>
                      <th>所属资产桶</th>
                      <th>类别</th>
                      <th>市场</th>
                      <th>风格属性</th>
                      <th>配置权重 (%)</th>
                      <th>预期股息率 (%)</th>
                      <th>折合年分红 (元)</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(state.board.assets).map(([code, asset]) => {
                      const annualDiv = (boardMetrics.investPrincipal * 10000) * ((asset.weight || 0) / 100.0) * ((asset.yield || 0) / 100.0);
                      const bucketTag = asset.bucket === 'safety' ? <span className="tag tag-green">🛡️ 防御桶</span> : (
                        asset.bucket === 'hedge' ? <span className="tag tag-purple">⚖️ 对冲桶</span> : <span className="tag tag-blue">🚀 成长桶</span>
                      );
                      return (
                        <tr key={code}>
                          <td><code>{code}</code></td>
                          <td><strong>{asset.name}</strong></td>
                          <td>{bucketTag}</td>
                          <td><span className="tag">{asset.category || 'Equity'}</span></td>
                          <td><span className="tag tag-blue">{asset.market}</span></td>
                          <td><span className="tag">{asset.style}</span></td>
                          <td>
                            <input 
                              type="number" 
                              className="input-control" 
                              style={{ width: '80px', padding: '4px 8px' }}
                              value={asset.weight}
                              step="1"
                              onChange={e => {
                                const val = parseFloat(e.target.value) || 0;
                                setState({
                                  ...state,
                                  board: {
                                    ...state.board,
                                    assets: {
                                      ...state.board.assets,
                                      [code]: { ...asset, weight: val }
                                    }
                                  }
                                });
                              }}
                            />
                          </td>
                          <td>{asset.yield}%</td>
                          <td style={{ color: '#38BDF8' }}>¥{Math.round(annualDiv).toLocaleString()}</td>
                          <td>
                            <button 
                              className="btn btn-danger btn-sm" 
                              style={{ padding: '2px 8px' }}
                              onClick={() => handleDeleteAsset(code)}
                              title="删除此标的"
                            >
                              ✕
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: 🩺 家庭资产体检与保障 (8大卡片 P2-4 & 完整录入表单 P0-5 & 房产双视角 P1-3) */}
        {activeTab === 'health' && (
          <div>
            {/* 置顶高息债务警报 */}
            {debtMetrics.hasHighInterestAlert && (
              <div style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: '2px solid #EF4444',
                borderRadius: '12px',
                padding: '16px 20px',
                marginBottom: '20px',
                boxShadow: '0 0 25px rgba(239, 68, 68, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <span style={{ fontSize: '32px' }}>🚨</span>
                  <div>
                    <div style={{ color: '#F87171', fontWeight: 700, fontSize: '1.05rem', marginBottom: '4px' }}>
                      【置顶健康警报】检测到家庭存在高息债务风险！
                    </div>
                    <div style={{ color: '#FECACA', fontSize: '0.86rem' }}>
                      当前自报高息债务余额 ¥{Number(state.debt?.highInterestDebtBalance || 0).toLocaleString()} 元，或综合贷款利率达到 &gt;6.0% (测算利率 {debtMetrics.effectiveDebtRate}%)。建议列为最高优先级偿还事项！
                    </div>
                  </div>
                </div>
                <button className="btn btn-danger btn-sm" onClick={() => handleJumpToModule('health', 'debt-decision-card')}>
                  直达债务决策
                </button>
              </div>
            )}

            {/* P2-4: 8 大核心财务体检总览指标卡 */}
            <div className="grid-8" style={{ marginBottom: '22px' }}>
              <div className="metric-card">
                <div className="metric-label">全口径家庭总净资产</div>
                <div className="metric-val" style={{ color: '#10B981', fontSize: '1.25rem' }}>
                  ¥{(realEstateMetrics.totalNetWorth / 10000).toFixed(0)} <span style={{ fontSize: '0.85rem' }}>万</span>
                </div>
                <div className="metric-sub">含房产 (总负债 ¥{(realEstateMetrics.totalDebt/10000).toFixed(0)}万)</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">纯金融净资产</div>
                <div className="metric-val" style={{ color: '#38BDF8', fontSize: '1.25rem' }}>
                  ¥{(realEstateMetrics.financialNetWorth / 10000).toFixed(0)} <span style={{ fontSize: '0.85rem' }}>万</span>
                </div>
                <div className="metric-sub">剔除房产与房贷 (变现性强)</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">月可支配结余</div>
                <div className="metric-val" style={{ color: '#FBBF24', fontSize: '1.25rem' }}>
                  ¥{Number(state.health.monthlySurplus).toLocaleString()}
                </div>
                <div className="metric-sub">月入 ¥{Number(state.health.monthlyIncome).toLocaleString()} · 支出 ¥{Number(state.health.monthlyExpense).toLocaleString()}</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">综合负债 / 月供占比</div>
                <div className="metric-val" style={{ fontSize: '1.25rem' }}>
                  {realEstateMetrics.normalDebtToAsset}%
                </div>
                <div className="metric-sub">
                  负债率 · 月供 ¥{Number(state.debt.monthlyDebtPayment || 0).toLocaleString()} (占比 {(Number(state.debt.monthlyDebtPayment || 0) / Number(state.health.monthlyIncome || 1) * 100).toFixed(0)}%)
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">流动性应急覆盖倍数</div>
                <div className="metric-val" style={{ color: liquidityMetrics.isCoverageInsufficient ? '#F87171' : '#34D399', fontSize: '1.25rem' }}>
                  {liquidityMetrics.coverageRatio}x
                </div>
                <div className="metric-sub">{liquidityMetrics.isCoverageInsufficient ? '⚠️ 短期应急储备不足' : '✅ 覆盖充裕 (安全线1.5x)'}</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">家庭人身保障健康度</div>
                <div className="metric-val" style={{ color: insuranceMetrics.shouldWarnAndDowngrade ? '#F87171' : '#34D399', fontSize: '1.25rem' }}>
                  {insuranceMetrics.shouldWarnAndDowngrade ? '严重缺位' : (!insuranceMetrics.hasMillionMedical ? '缺百万医疗' : '基础健全')}
                </div>
                <div className="metric-sub">寿险缺口: ¥{(insuranceMetrics.lifeGap/10000).toFixed(0)}万</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">财务脆弱性评分</div>
                <div className="metric-val" style={{ color: explainableScores.totalVulnerability > 50 ? '#F87171' : (explainableScores.totalVulnerability > 25 ? '#FBBF24' : '#10B981'), fontSize: '1.25rem' }}>
                  {explainableScores.totalVulnerability} <span style={{ fontSize: '0.85rem' }}>分</span>
                </div>
                <div className="metric-sub">{explainableScores.vulnerabilityLevel} (越低越健康)</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">客观行为进攻性</div>
                <div className="metric-val" style={{ color: '#C084FC', fontSize: '1.25rem' }}>
                  {explainableScores.totalAggressiveness} <span style={{ fontSize: '0.85rem' }}>分</span>
                </div>
                <div className="metric-sub">{explainableScores.aggressivenessLevel} (纯行为测算)</div>
              </div>
            </div>

            {/* P0-5: 完整家庭财务体检基础信息录入区 */}
            <div className="card" style={{ marginBottom: '20px' }}>
              <div className="card-header">
                <div className="card-title">
                  <span>📝 家庭收支、现状资产分层与负债明细全量录入</span>
                </div>
                <span style={{ fontSize: '0.78rem', color: '#94A3B8' }}>
                  双向实时绑定 · 数据完全存入本地 localStorage
                </span>
              </div>

              {/* 1. 基础收支与稳定性 */}
              <div style={{ fontWeight: 700, color: '#38BDF8', fontSize: '0.88rem', marginBottom: '10px' }}>
                1. 基础收支结构与职业抗风险力
              </div>
              <div className="grid-6" style={{ marginBottom: '16px' }}>
                <div className="form-group">
                  <label className="form-label">家庭月收入 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.monthlyIncome} 
                    step="1000"
                    onChange={e => {
                      const inc = parseFloat(e.target.value) || 0;
                      const exp = state.health.monthlyExpense || 0;
                      setState({ ...state, health: { ...state.health, monthlyIncome: inc, monthlySurplus: Math.max(0, inc - exp) } });
                    }}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">常规月支出 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.monthlyExpense} 
                    step="1000"
                    onChange={e => {
                      const exp = parseFloat(e.target.value) || 0;
                      const inc = state.health.monthlyIncome || 0;
                      setState({ ...state, health: { ...state.health, monthlyExpense: exp, monthlySurplus: Math.max(0, inc - exp) } });
                    }}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">必要生活底线 (元/月)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.essentialMonthlyExpense} 
                    step="1000"
                    onChange={e => setState({ ...state, health: { ...state.health, essentialMonthlyExpense: parseFloat(e.target.value) || 0 } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">月可结余 (自动计算)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.monthlySurplus} 
                    disabled 
                    style={{ background: 'rgba(0,0,0,0.3)', color: '#34D399', fontWeight: 700 }}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">收入来源结构</label>
                  <select 
                    className="input-control"
                    value={state.health.incomeSourceCount || 'dual'}
                    onChange={e => setState({ ...state, health: { ...state.health, incomeSourceCount: e.target.value } })}
                  >
                    <option value="dual">双薪家庭 (稳定分散)</option>
                    <option value="single">单薪家庭 (主干依赖高)</option>
                    <option value="multiple">多元收入 (经营/副业/被动)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">预期失业恢复期 (月)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.unemploymentRecoveryMonths || 6} 
                    min="1" max="36"
                    onChange={e => setState({ ...state, health: { ...state.health, unemploymentRecoveryMonths: parseInt(e.target.value) || 6 } })}
                  />
                </div>
              </div>

              {/* 2. A组：家庭现状资产分层 */}
              <div style={{ fontWeight: 700, color: '#38BDF8', fontSize: '0.88rem', marginBottom: '10px' }}>
                2. A组：家庭现状资产分层结构 (当前存量)
              </div>
              <div className="grid-4" style={{ marginBottom: '16px' }}>
                <div className="form-group">
                  <label className="form-label">活期现金 / 银行存款 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.assetsBreakdown?.cashCurrent ?? 100000} 
                    step="10000"
                    onChange={e => setState({ ...state, health: { ...state.health, assetsBreakdown: { ...state.health.assetsBreakdown, cashCurrent: parseFloat(e.target.value) || 0 } } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">货币基金 / 短期理财 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.assetsBreakdown?.cashShortDebt ?? 200000} 
                    step="10000"
                    onChange={e => setState({ ...state, health: { ...state.health, assetsBreakdown: { ...state.health.assetsBreakdown, cashShortDebt: parseFloat(e.target.value) || 0 } } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">股票 / 权益基金 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.assetsBreakdown?.equityAssets ?? 440000} 
                    step="10000"
                    onChange={e => setState({ ...state, health: { ...state.health, assetsBreakdown: { ...state.health.assetsBreakdown, equityAssets: parseFloat(e.target.value) || 0 } } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">黄金 / 贵金属资产 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.assetsBreakdown?.goldAssets ?? 56000} 
                    step="5000"
                    onChange={e => setState({ ...state, health: { ...state.health, assetsBreakdown: { ...state.health.assetsBreakdown, goldAssets: parseFloat(e.target.value) || 0 } } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">中长债 / 固收产品 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.assetsBreakdown?.bondAssets ?? 184000} 
                    step="10000"
                    onChange={e => setState({ ...state, health: { ...state.health, assetsBreakdown: { ...state.health.assetsBreakdown, bondAssets: parseFloat(e.target.value) || 0 } } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">自住/投资房产总估值 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.property.totalEstimatedValue} 
                    step="100000"
                    onChange={e => {
                      const v = parseFloat(e.target.value) || 0;
                      setState({ 
                        ...state, 
                        property: { ...state.property, totalEstimatedValue: v },
                        health: { ...state.health, assetsBreakdown: { ...state.health.assetsBreakdown, propertyEstimated: v } }
                      });
                    }}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">个人养老金现值 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.assetsBreakdown?.pensionCashValue ?? 20000} 
                    step="5000"
                    onChange={e => setState({ ...state, health: { ...state.health, assetsBreakdown: { ...state.health.assetsBreakdown, pensionCashValue: parseFloat(e.target.value) || 0 } } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">其他流动资产 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.assetsBreakdown?.otherAssets ?? 0} 
                    step="10000"
                    onChange={e => setState({ ...state, health: { ...state.health, assetsBreakdown: { ...state.health.assetsBreakdown, otherAssets: parseFloat(e.target.value) || 0 } } })}
                  />
                </div>
              </div>

              {/* 3. 负债明细录入 (P0-3 包含利率与开关) */}
              <div style={{ fontWeight: 700, color: '#38BDF8', fontSize: '0.88rem', marginBottom: '10px' }}>
                3. 家庭负债明细与利率参数
              </div>
              <div className="grid-6" style={{ marginBottom: '16px' }}>
                <div className="form-group">
                  <label className="form-label">商业房贷余额 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.debt.mortgageBalance} 
                    step="50000"
                    onChange={e => setState({ ...state, debt: { ...state.debt, mortgageBalance: parseFloat(e.target.value) || 0 } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">车贷余额 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.debt.carLoanBalance} 
                    step="10000"
                    onChange={e => setState({ ...state, debt: { ...state.debt, carLoanBalance: parseFloat(e.target.value) || 0 } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">消费贷/信用贷 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.debt.consumerLoanBalance} 
                    step="10000"
                    onChange={e => setState({ ...state, debt: { ...state.debt, consumerLoanBalance: parseFloat(e.target.value) || 0 } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">经营贷余额 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.debt.businessLoanBalance} 
                    step="50000"
                    onChange={e => setState({ ...state, debt: { ...state.debt, businessLoanBalance: parseFloat(e.target.value) || 0 } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">每月还贷总额 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.debt.monthlyDebtPayment} 
                    step="500"
                    onChange={e => setState({ ...state, debt: { ...state.debt, monthlyDebtPayment: parseFloat(e.target.value) || 0 } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">剩余还贷年限 (年)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.debt.remainingYears || 15} 
                    min="1" max="35"
                    onChange={e => setState({ ...state, debt: { ...state.debt, remainingYears: parseInt(e.target.value) || 15 } })}
                  />
                </div>
              </div>

              <div className="grid-3" style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', marginBottom: '16px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">综合贷款利率档位</label>
                  <select 
                    className="input-control"
                    value={state.debt.debtRateBracket}
                    disabled={state.debt.useCustomRate}
                    onChange={e => setState({ ...state, debt: { ...state.debt, debtRateBracket: e.target.value } })}
                  >
                    {Object.entries(DEBT_RATE_BRACKETS).map(([k, v]) => (
                      <option key={k} value={k}>{v.label}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">自定义合同利率 (%)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input 
                      type="checkbox" 
                      id="use-custom-rate"
                      checked={state.debt.useCustomRate || false}
                      onChange={e => setState({ ...state, debt: { ...state.debt, useCustomRate: e.target.checked } })}
                      style={{ width: '16px', height: '16px' }}
                    />
                    <input 
                      type="number" 
                      className="input-control"
                      style={{ flex: 1 }}
                      placeholder="如 3.85"
                      step="0.05"
                      value={state.debt.customDebtRate ?? ''}
                      disabled={!state.debt.useCustomRate}
                      onChange={e => setState({ ...state, debt: { ...state.debt, customDebtRate: parseFloat(e.target.value) || null } })}
                    />
                  </div>
                </div>

                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">自报高息债务余额 (&gt;6%利息, 元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.debt.highInterestDebtBalance || 0} 
                    step="10000"
                    onChange={e => setState({ ...state, debt: { ...state.debt, highInterestDebtBalance: parseFloat(e.target.value) || 0 } })}
                  />
                </div>
              </div>

              {/* 4. B组：未来确定性支出 */}
              <div style={{ fontWeight: 700, color: '#38BDF8', fontSize: '0.88rem', marginBottom: '10px' }}>
                4. B组：未来 1-5 年大额确定性支出 (刚需隔离资金)
              </div>
              <div className="grid-3">
                <div className="form-group">
                  <label className="form-label">未来 12 个月内大额支出 (元, 100%隔离)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.expectedExpenses?.expense1y ?? 100000} 
                    step="10000"
                    onChange={e => setState({ ...state, health: { ...state.health, bucket1y: parseFloat(e.target.value) || 0, expectedExpenses: { ...state.health.expectedExpenses, expense1y: parseFloat(e.target.value) || 0 } } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">未来 1-3 年大额支出 (元, 50%折减隔离)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.expectedExpenses?.expense1To3y ?? 150000} 
                    step="10000"
                    onChange={e => setState({ ...state, health: { ...state.health, bucket1To3y: parseFloat(e.target.value) || 0, expectedExpenses: { ...state.health.expectedExpenses, expense1To3y: parseFloat(e.target.value) || 0 } } })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">未来 3-5 年大额支出 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={state.health.expectedExpenses?.expense3To5y ?? 100000} 
                    step="10000"
                    onChange={e => setState({ ...state, health: { ...state.health, bucket3To5y: parseFloat(e.target.value) || 0, expectedExpenses: { ...state.health.expectedExpenses, expense3To5y: parseFloat(e.target.value) || 0 } } })}
                  />
                </div>
              </div>
            </div>

            {/* 1. 家庭保障缺口测算 (责任缺口法 P1-2) */}
            <div className="card" id="insurance-gap-card">
              <div className="card-header">
                <div className="card-title">
                  <span>🛡️ 家庭保障缺口测算 (责任缺口法模型)</span>
                  <span className={`tag ${insuranceMetrics.shouldWarnAndDowngrade ? 'tag-red' : 'tag-green'}`}>
                    {insuranceMetrics.shouldWarnAndDowngrade ? '⚠️ 基础保障严重缺位' : '✅ 保障底线健全'}
                  </span>
                </div>
              </div>

              <div className="grid-4" style={{ marginBottom: '16px' }}>
                <div className="form-group">
                  <label className="form-label">行业收入稳定性</label>
                  <select 
                    className="input-control"
                    value={state.insurance.stabilityTier}
                    onChange={e => setState({ ...state, insurance: { ...state.insurance, stabilityTier: e.target.value } })}
                  >
                    <option value="high">高稳定 (体制内/垄断国企: 3年+30万)</option>
                    <option value="medium">中等稳定 (成熟实业/外企: 4年+40万)</option>
                    <option value="low">波动大 (互联网/初创/销售: 5年+50万)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">保障覆盖程度自评</label>
                  <select 
                    className="input-control"
                    value={state.insurance.coverageTier}
                    onChange={e => setState({ ...state, insurance: { ...state.insurance, coverageTier: e.target.value } })}
                  >
                    {INSURANCE_COVERAGE_TIERS.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">子女教育金保障目标 (元)</label>
                  <input 
                    type="number" 
                    className="input-control"
                    value={state.insurance.childEduTarget ?? 500000}
                    step="50000"
                    onChange={e => setState({ ...state, insurance: { ...state.insurance, childEduTarget: parseFloat(e.target.value) || 0 } })}
                  />
                  <small style={{ color: '#94A3B8', fontSize: '0.72rem' }}>独立用于寿险责任总需求汇总</small>
                </div>

                <div className="form-group">
                  <label className="form-label">百万医疗险兜底检查</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', height: '38px' }}>
                    <input 
                      type="checkbox" 
                      id="has-mil-med"
                      checked={state.insurance.hasMillionMedical}
                      onChange={e => setState({ ...state, insurance: { ...state.insurance, hasMillionMedical: e.target.checked } })}
                      style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                    />
                    <label htmlFor="has-mil-med" style={{ cursor: 'pointer', fontSize: '0.85rem' }}>
                      {state.insurance.hasMillionMedical ? '✅ 已配置 (大额自费兜底)' : '❌ 未配置 (大额自费击穿)'}
                    </label>
                  </div>
                </div>
              </div>

              {/* 表格明细 */}
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>保障险种</th>
                      <th>量化责任需求目标</th>
                      <th>扣减高流动性现金</th>
                      <th>已有商业保额</th>
                      <th>净保障缺口</th>
                      <th>年收入倍数</th>
                      <th>配置建议</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><strong>定期寿险</strong></td>
                      <td>¥{Math.round(insuranceMetrics.lifeTarget).toLocaleString()} 元</td>
                      <td style={{ color: '#38BDF8' }}>-¥{insuranceMetrics.liquidCashDeduction.toLocaleString()} 元</td>
                      <td>
                        <input 
                          type="number" 
                          className="input-control" 
                          style={{ width: '120px', padding: '4px 8px' }}
                          value={state.insurance.existingLifeCover}
                          step="100000"
                          onChange={e => setState({ ...state, insurance: { ...state.insurance, existingLifeCover: parseFloat(e.target.value) || 0 } })}
                        />
                      </td>
                      <td style={{ fontWeight: 700, color: insuranceMetrics.lifeGap > 0 ? '#F87171' : '#34D399' }}>
                        ¥{insuranceMetrics.lifeGap.toLocaleString()} 元
                      </td>
                      <td>{insuranceMetrics.lifeGapIncomeMultiple}x 年收入</td>
                      <td>{insuranceMetrics.lifeGap > 0 ? '覆盖负债+10年生活底线+教育金' : '寿险额度充足'}</td>
                    </tr>
                    <tr>
                      <td><strong>重疾险</strong></td>
                      <td>¥{Math.round(insuranceMetrics.critTarget).toLocaleString()} 元</td>
                      <td style={{ color: '#94A3B8' }}>--</td>
                      <td>
                        <input 
                          type="number" 
                          className="input-control" 
                          style={{ width: '120px', padding: '4px 8px' }}
                          value={state.insurance.existingCritCover}
                          step="50000"
                          onChange={e => setState({ ...state, insurance: { ...state.insurance, existingCritCover: parseFloat(e.target.value) || 0 } })}
                        />
                      </td>
                      <td style={{ fontWeight: 700, color: insuranceMetrics.critGap > 0 ? '#F87171' : '#34D399' }}>
                        ¥{insuranceMetrics.critGap.toLocaleString()} 元
                      </td>
                      <td>{insuranceMetrics.critGapIncomeMultiple}x 年收入</td>
                      <td>{insuranceMetrics.critGap > 0 ? `补偿${insuranceMetrics.stabConfig.years}年收入+康复金` : '重疾防线达标'}</td>
                    </tr>
                    <tr>
                      <td><strong>综合意外险</strong></td>
                      <td>¥{insuranceMetrics.accidentTarget.toLocaleString()} 元</td>
                      <td style={{ color: '#94A3B8' }}>--</td>
                      <td>
                        <input 
                          type="number" 
                          className="input-control" 
                          style={{ width: '120px', padding: '4px 8px' }}
                          value={state.insurance.existingAccidentCover}
                          step="100000"
                          onChange={e => setState({ ...state, insurance: { ...state.insurance, existingAccidentCover: parseFloat(e.target.value) || 0 } })}
                        />
                      </td>
                      <td style={{ fontWeight: 700, color: insuranceMetrics.accidentGap > 0 ? '#F87171' : '#34D399' }}>
                        ¥{insuranceMetrics.accidentGap.toLocaleString()} 元
                      </td>
                      <td>{insuranceMetrics.accidentGapIncomeMultiple}x 年收入</td>
                      <td>保费低杠杆高，寿险缺口 50% 锚定</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* 2. 房产双视角资产负债表与极端冲击 (P1-3) */}
            <div className="card" id="property-card">
              <div className="card-header">
                <div className="card-title">
                  <span>🏠 全口径 vs 剔除房产双视角资产负债表 (房产下跌 20% 冲击模拟)</span>
                  <span className={`tag ${realEstateMetrics.tier === 'green' ? 'tag-green' : (realEstateMetrics.tier === 'yellow' ? 'tag-yellow' : 'tag-red')}`}>
                    房产占比: {realEstateMetrics.realEstateRatio}% ({realEstateMetrics.tier === 'green' ? '健康' : '偏高'})
                  </span>
                </div>
              </div>

              <div className="table-container" style={{ marginBottom: '14px' }}>
                <table>
                  <thead>
                    <tr>
                      <th>视角与情景</th>
                      <th>总资产口径</th>
                      <th>总负债口径</th>
                      <th>家庭净资产</th>
                      <th>资产负债率</th>
                      <th>净资产变动</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><strong>全口径视角 (含房产)</strong></td>
                      <td>¥{Math.round(realEstateMetrics.totalAssets).toLocaleString()} 元</td>
                      <td>¥{Math.round(realEstateMetrics.totalDebt).toLocaleString()} 元</td>
                      <td style={{ fontWeight: 700, color: '#10B981' }}>¥{Math.round(realEstateMetrics.totalNetWorth).toLocaleString()} 元</td>
                      <td><strong>{realEstateMetrics.normalDebtToAsset}%</strong></td>
                      <td>基准状态</td>
                    </tr>
                    <tr>
                      <td><strong>剔除房产口径 (纯金融投资)</strong></td>
                      <td>¥{Math.round(realEstateMetrics.financialAssets).toLocaleString()} 元</td>
                      <td>¥{Math.round(realEstateMetrics.financialDebt).toLocaleString()} 元</td>
                      <td style={{ fontWeight: 700, color: '#38BDF8' }}>¥{Math.round(realEstateMetrics.financialNetWorth).toLocaleString()} 元</td>
                      <td><strong>{realEstateMetrics.financialDebtRatio}%</strong></td>
                      <td>反映真实流动偿债实力</td>
                    </tr>
                    <tr style={{ background: 'rgba(239, 68, 68, 0.06)' }}>
                      <td><strong>房产下跌 {realEstateMetrics.stressDropPct}% 压力冲击</strong></td>
                      <td>¥{Math.round(realEstateMetrics.stressTotalAssets).toLocaleString()} 元</td>
                      <td>¥{Math.round(realEstateMetrics.totalDebt).toLocaleString()} 元</td>
                      <td style={{ fontWeight: 700, color: '#F87171' }}>¥{Math.round(realEstateMetrics.stressTotalNetWorth).toLocaleString()} 元</td>
                      <td><strong style={{ color: '#F87171' }}>{realEstateMetrics.stressDebtToAsset}%</strong></td>
                      <td style={{ color: '#F87171' }}>缩水 ¥{Math.round(realEstateMetrics.stressDropAmount).toLocaleString()} 元</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '12px 16px', borderRadius: '8px', fontSize: '0.82rem', color: '#CBD5E1' }}>
                💡 <strong>集中度分析</strong>：{realEstateMetrics.tierAdvice}
              </div>
            </div>

            {/* 3. 债务决策对照矩阵 (P0-3, P1-4 利差符号对齐与来源标识) */}
            <div className="card" id="debt-decision-card">
              <div className="card-header">
                <div className="card-title">
                  <span>⚖️ 债务决策对照：提前还贷 vs 组合投资路径模拟</span>
                  <span className="tag tag-blue">{debtMetrics.sourceBadge}</span>
                </div>
                <span style={{ fontSize: '0.78rem', color: '#94A3B8' }}>
                  简化复利终值对照模型 · 未计入等额本息本金折减与税费摩擦
                </span>
              </div>

              <div className="grid-3" style={{ marginBottom: '14px' }}>
                <div className="metric-card">
                  <div className="metric-label">综合贷款测算利率</div>
                  <div className="metric-val" style={{ color: debtMetrics.effectiveDebtRate > 6 ? '#F87171' : '#FBBF24' }}>
                    {debtMetrics.effectiveDebtRate.toFixed(2)}%
                  </div>
                  <div className="metric-sub">{debtMetrics.sourceBadge} (剩余 {debtMetrics.remainingYears} 年)</div>
                </div>

                <div className="metric-card">
                  <div className="metric-label">组合保守预期收益率</div>
                  <div className="metric-val" style={{ color: '#10B981' }}>
                    {debtMetrics.conservativeYield.toFixed(2)}%
                  </div>
                  <div className="metric-sub">取增长预期 {debtMetrics.growthRate}% 的 70% 保守基准</div>
                </div>

                <div className="metric-card">
                  <div className="metric-label">利差对比 (保守收益率 − 贷款利率)</div>
                  <div className="metric-val" style={{ color: debtMetrics.spread >= 0 ? '#34D399' : '#F87171' }}>
                    {debtMetrics.spread >= 0 ? '+' : ''}{debtMetrics.spread.toFixed(2)}%
                  </div>
                  <div className="metric-sub">{debtMetrics.spreadLabel}</div>
                </div>
              </div>

              <div style={{
                background: debtMetrics.decisionType === 'repay_first' ? 'rgba(239, 68, 68, 0.12)' : (debtMetrics.decisionType === 'invest_first' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(56, 189, 248, 0.12)'),
                border: `1px solid ${debtMetrics.decisionType === 'repay_first' ? '#EF4444' : (debtMetrics.decisionType === 'invest_first' ? '#10B981' : '#38BDF8')}`,
                padding: '14px 18px',
                borderRadius: '8px',
                marginBottom: '16px',
                fontSize: '0.88rem'
              }}>
                📢 <strong>决策矩阵研判结论</strong>：{debtMetrics.decisionText}
              </div>

              {/* 路径模拟表格 */}
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>模拟周期</th>
                      <th>模拟资金 X (本金)</th>
                      <th>路径 A: 提前还贷终值效应</th>
                      <th>路径 B: 坚持投资推演终值</th>
                      <th>净资产差额 (A − B)</th>
                      <th>策略对比建议</th>
                    </tr>
                  </thead>
                  <tbody>
                    {debtMetrics.comparisonTable.map(row => (
                      <tr key={row.years}>
                        <td><strong>{row.years} 年期</strong></td>
                        <td>¥{row.fundX.toLocaleString()}</td>
                        <td>¥{row.fvRepay.toLocaleString()}</td>
                        <td>¥{row.fvInvest.toLocaleString()}</td>
                        <td style={{ fontWeight: 700, color: row.diff > 0 ? '#F87171' : '#34D399' }}>
                          {row.diff > 0 ? `+¥${row.diff.toLocaleString()}` : `-¥${Math.abs(row.diff).toLocaleString()}`}
                        </td>
                        <td><strong>{row.advantage}</strong></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 4. 个人养老金税优卡片 */}
            <div className="card" id="pension-card">
              <div className="card-header">
                <div className="card-title">
                  <span>👵 个人养老金税优检查与递延省税推演</span>
                </div>
              </div>

              <div className="grid-3">
                <div className="metric-card">
                  <div className="metric-label">本年度剩余可用额度</div>
                  <div className="metric-val">¥{pensionMetrics.remainingQuota.toLocaleString()}</div>
                  <div className="metric-sub">额度跨年作废，无法累计</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">放弃的当期税收抵扣额</div>
                  <div className="metric-val" style={{ color: '#FBBF24' }}>¥{pensionMetrics.annualTaxSavingsForegone.toLocaleString()} /年</div>
                  <div className="metric-sub">按边际税率 {(pensionMetrics.taxRate*100).toFixed(0)}% 估算</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">20年累计放弃节税估算</div>
                  <div className="metric-val" style={{ color: '#38BDF8' }}>¥{pensionMetrics.cumulative20ySavings.toLocaleString()}</div>
                  <div className="metric-sub">长线递延抵税收益</div>
                </div>
              </div>

              <div style={{ marginTop: '12px', padding: '10px 14px', background: 'rgba(16, 185, 129, 0.08)', borderRadius: '8px', fontSize: '0.82rem', color: '#6EE7B7' }}>
                💡 <strong>标的指引建议</strong>：{pensionMetrics.guidanceText}
              </div>
            </div>

            {/* 5. 可解释评分卡片 (P1-6 7因子脆弱性 + P1-7 4因子客观进攻性) */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <span>📊 综合财务评分与可解释归因归因透视</span>
                </div>
                <button className="btn btn-outline btn-sm" onClick={() => setShowScoreBreakdown(!showScoreBreakdown)}>
                  {showScoreBreakdown ? '收起因子明细' : '查看因子详细拆解'}
                </button>
              </div>

              <div className="grid-2" style={{ marginBottom: '14px' }}>
                <div style={{ background: 'rgba(0,0,0,0.25)', padding: '16px', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.85rem', color: '#94A3B8', marginBottom: '4px' }}>财务脆弱性评分 (越低越稳健)</div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 700, color: explainableScores.totalVulnerability > 50 ? '#F87171' : '#34D399' }}>
                    {explainableScores.totalVulnerability} <span style={{ fontSize: '1rem', color: '#94A3B8' }}>/ 100分</span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#CBD5E1', marginTop: '6px' }}>
                    {explainableScores.worstVulnConclusion}
                  </div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.25)', padding: '16px', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.85rem', color: '#94A3B8', marginBottom: '4px' }}>客观理财进攻性评分 (纯行为持仓度量)</div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#C084FC' }}>
                    {explainableScores.totalAggressiveness} <span style={{ fontSize: '1rem', color: '#94A3B8' }}>/ 100分</span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#CBD5E1', marginTop: '6px' }}>
                    评级：<strong>{explainableScores.aggressivenessLevel}</strong>（由严格权益仓位、高波动海外暴露、负债杠杆等客观行为驱动）
                  </div>
                </div>
              </div>

              {showScoreBreakdown && (
                <div className="grid-2" style={{ gap: '16px', marginTop: '12px' }}>
                  <div style={{ background: 'rgba(255,255,255,0.02)', padding: '14px', borderRadius: '8px' }}>
                    <div style={{ fontWeight: 700, color: '#F87171', fontSize: '0.88rem', marginBottom: '8px' }}>
                      🛡️ 7 大财务脆弱性归因子明细：
                    </div>
                    {explainableScores.vulnFactors.map((f, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: '0.8rem' }}>
                        <span>{f.name} <small style={{ color: '#94A3B8' }}>({f.desc})</small></span>
                        <strong style={{ color: f.score > (f.max * 0.5) ? '#F87171' : '#34D399' }}>
                          {f.score} / {f.max} 分
                        </strong>
                      </div>
                    ))}
                  </div>

                  <div style={{ background: 'rgba(255,255,255,0.02)', padding: '14px', borderRadius: '8px' }}>
                    <div style={{ fontWeight: 700, color: '#C084FC', fontSize: '0.88rem', marginBottom: '8px' }}>
                      🚀 4 大客观行为进攻性因子明细：
                    </div>
                    {explainableScores.aggFactors.map((f, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: '0.8rem' }}>
                        <span>{f.name} <small style={{ color: '#94A3B8' }}>({f.desc})</small></span>
                        <strong style={{ color: '#C084FC' }}>
                          {f.score} / {f.max} 分
                        </strong>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: ⏱️ 缓冲池与复合压力测试 (失业模型 P0-1 & 历史回放 P0-2 & 4情景联测 P2-5) */}
        {activeTab === 'buffer' && (
          <div>
            {/* 常规基准平滑指标 */}
            <div className="grid-3" style={{ marginBottom: '20px' }}>
              <div className="metric-card">
                <div className="metric-label">缓冲池初始种子金</div>
                <div className="metric-val">¥{(state.board.bufferSeed * 10000).toLocaleString()}</div>
                <div className="metric-sub">闲置年化利率: {state.board.moneyMarketRate}%</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">36 个月基准最低水位</div>
                <div className="metric-val" style={{ color: bufferMetrics.isBufferSafe ? '#10B981' : '#F43F5E' }}>
                  ¥{Math.round(bufferMetrics.minBuffer).toLocaleString()}
                </div>
                <div className="metric-sub">{bufferMetrics.isBufferSafe ? '✅ 安全平滑 (无亏空)' : '⚠️ 出现负余额断流'}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">最脆弱月份</div>
                <div className="metric-val" style={{ color: '#FBBF24' }}>第 {bufferMetrics.mostFragileMonth} 个月</div>
                <div className="metric-sub">全周期内资金压力最大时点</div>
              </div>
            </div>

            {/* P2-5: 四大复合情景同时联测与横向对比卡片 */}
            <div className="card" id="buffer-simulation-card">
              <div className="card-header">
                <div className="card-title">
                  <span>⚡ 四大极端情景复合压力测试横向对比</span>
                  <span className={`tag ${!fourStressSimulations.worst.sim.isExhausted ? 'tag-green' : 'tag-red'}`}>
                    最严酷: {fourStressSimulations.worst.name}
                  </span>
                </div>
              </div>

              {/* 置顶最严酷情景通报徽章 */}
              <div style={{
                background: fourStressSimulations.worst.sim.isExhausted ? 'rgba(239, 68, 68, 0.12)' : 'rgba(16, 185, 129, 0.12)',
                border: `1px solid ${fourStressSimulations.worst.sim.isExhausted ? '#EF4444' : '#10B981'}`,
                padding: '12px 18px',
                borderRadius: '8px',
                marginBottom: '16px',
                fontSize: '0.86rem'
              }}>
                📢 <strong>四大情景联测结论</strong>：
                {fourStressSimulations.worst.sim.isExhausted ? (
                  <span>
                    在【<strong>{fourStressSimulations.worst.name}</strong>】下，缓冲池将于<strong>第 {fourStressSimulations.worst.sim.exhaustionMonth} 个月耗尽枯竭</strong>！需按回撤折价变现资产 <strong>¥{fourStressSimulations.worst.sim.minAssetToSell.toLocaleString()} 元</strong>，恢复需 <strong>{fourStressSimulations.worst.sim.monthsToRecover} 个月</strong>。
                  </span>
                ) : (
                  <span>家庭缓冲池实力强劲，全程成功抵御所有 4 大复合极端压力冲击，未发生穿透断流！</span>
                )}
              </div>

              {/* 4情景横向对比表格 */}
              <div className="table-container" style={{ marginBottom: '18px' }}>
                <table>
                  <thead>
                    <tr>
                      <th>测试情景</th>
                      <th>核心假设特征</th>
                      <th>缓冲池状态</th>
                      <th>最早枯竭时点</th>
                      <th>极限最低水位 / 需变现资产</th>
                      <th>恢复所需月数</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><strong>标准复合情景</strong></td>
                      <td>失业6月(替代率{(replacementRate*100).toFixed(0)}%)+分红降30%+回撤20%</td>
                      <td>
                        <span className={`tag ${fourStressSimulations.standard.isExhausted ? 'tag-red' : 'tag-green'}`}>
                          {fourStressSimulations.standard.isExhausted ? '🔴 枯竭' : '🟢 平稳'}
                        </span>
                      </td>
                      <td>{fourStressSimulations.standard.isExhausted ? `第 ${fourStressSimulations.standard.exhaustionMonth} 月` : '未枯竭'}</td>
                      <td>{fourStressSimulations.standard.isExhausted ? `需变现 ¥${fourStressSimulations.standard.minAssetToSell.toLocaleString()}` : `最低 ¥${fourStressSimulations.standard.minBuffer.toLocaleString()}`}</td>
                      <td>{fourStressSimulations.standard.monthsToRecover} 个月</td>
                    </tr>
                    <tr>
                      <td><strong>严重复合情景</strong></td>
                      <td>失业12月+分红降50%+回撤35%+医疗20万</td>
                      <td>
                        <span className={`tag ${fourStressSimulations.severe.isExhausted ? 'tag-red' : 'tag-green'}`}>
                          {fourStressSimulations.severe.isExhausted ? '🔴 枯竭' : '🟢 平稳'}
                        </span>
                      </td>
                      <td>{fourStressSimulations.severe.isExhausted ? `第 ${fourStressSimulations.severe.exhaustionMonth} 月` : '未枯竭'}</td>
                      <td>{fourStressSimulations.severe.isExhausted ? `需变现 ¥${fourStressSimulations.severe.minAssetToSell.toLocaleString()}` : `最低 ¥${fourStressSimulations.severe.minBuffer.toLocaleString()}`}</td>
                      <td>{fourStressSimulations.severe.monthsToRecover} 个月</td>
                    </tr>
                    <tr>
                      <td><strong>滞胀情景</strong></td>
                      <td>通胀5%(生活费递增)+延迟4月+分红降20%</td>
                      <td>
                        <span className={`tag ${fourStressSimulations.stagflation.isExhausted ? 'tag-red' : 'tag-green'}`}>
                          {fourStressSimulations.stagflation.isExhausted ? '🔴 枯竭' : '🟢 平稳'}
                        </span>
                      </td>
                      <td>{fourStressSimulations.stagflation.isExhausted ? `第 ${fourStressSimulations.stagflation.exhaustionMonth} 月` : '未枯竭'}</td>
                      <td>{fourStressSimulations.stagflation.isExhausted ? `需变现 ¥${fourStressSimulations.stagflation.minAssetToSell.toLocaleString()}` : `最低 ¥${fourStressSimulations.stagflation.minBuffer.toLocaleString()}`}</td>
                      <td>{fourStressSimulations.stagflation.monthsToRecover} 个月</td>
                    </tr>
                    <tr>
                      <td><strong>{HISTORICAL_REPLAYS[state.stress.selectedReplayId]?.name || '历史回放'}</strong></td>
                      <td>{HISTORICAL_REPLAYS[state.stress.selectedReplayId]?.description || '真实回撤曲线'}</td>
                      <td>
                        <span className={`tag ${fourStressSimulations.replay.isExhausted ? 'tag-red' : 'tag-green'}`}>
                          {fourStressSimulations.replay.isExhausted ? '🔴 枯竭' : '🟢 平稳'}
                        </span>
                      </td>
                      <td>{fourStressSimulations.replay.isExhausted ? `第 ${fourStressSimulations.replay.exhaustionMonth} 月` : '未枯竭'}</td>
                      <td>{fourStressSimulations.replay.isExhausted ? `需变现 ¥${fourStressSimulations.replay.minAssetToSell.toLocaleString()}` : `最低 ¥${fourStressSimulations.replay.minBuffer.toLocaleString()}`}</td>
                      <td>{fourStressSimulations.replay.monthsToRecover} 个月</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* 情景详细交互与失业模型参数 (P0-1) */}
              <div style={{ background: 'rgba(0,0,0,0.25)', padding: '14px', borderRadius: '10px', marginBottom: '18px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#38BDF8' }}>
                    🎛️ 单情景深度推演参数调控
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <label style={{ fontSize: '0.8rem', color: '#94A3B8' }}>失业收入替代率 ({((state.stress.unemploymentReplacementRate ?? 0.3) * 100).toFixed(0)}%):</label>
                    <input 
                      type="range"
                      min="0" max="1" step="0.05"
                      value={state.stress.unemploymentReplacementRate ?? 0.3}
                      onChange={e => setState({ ...state, stress: { ...state.stress, unemploymentReplacementRate: parseFloat(e.target.value) } })}
                      style={{ width: '120px' }}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '14px' }}>
                  <button 
                    className={`btn ${state.stress.scenarioType === 'preset' && state.stress.selectedPresetId === 'standard' ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setState({ ...state, stress: { ...state.stress, scenarioType: 'preset', selectedPresetId: 'standard' } })}
                  >
                    标准复合 (失业6月+分红降30%+回撤20%)
                  </button>
                  <button 
                    className={`btn ${state.stress.scenarioType === 'preset' && state.stress.selectedPresetId === 'severe' ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setState({ ...state, stress: { ...state.stress, scenarioType: 'preset', selectedPresetId: 'severe' } })}
                  >
                    严重复合 (失业12月+分红降50%+回撤35%+医疗20万)
                  </button>
                  <button 
                    className={`btn ${state.stress.scenarioType === 'preset' && state.stress.selectedPresetId === 'stagflation' ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setState({ ...state, stress: { ...state.stress, scenarioType: 'preset', selectedPresetId: 'stagflation' } })}
                  >
                    滞胀情景 (通胀5%+延迟4月+分红降20%)
                  </button>
                  <button 
                    className={`btn ${state.stress.scenarioType === 'replay' ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setState({ ...state, stress: { ...state.stress, scenarioType: 'replay' } })}
                  >
                    历史周期回放模板 (2018/2022/2015)
                  </button>
                </div>

                {/* 历史回放模板子选项 (P0-2) */}
                {state.stress.scenarioType === 'replay' && (
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
                      {Object.values(HISTORICAL_REPLAYS).map(rep => (
                        <button
                          key={rep.id}
                          className={`btn btn-sm ${state.stress.selectedReplayId === rep.id ? 'btn-primary' : 'btn-outline'}`}
                          onClick={() => setState({ ...state, stress: { ...state.stress, selectedReplayId: rep.id } })}
                        >
                          {rep.name}
                        </button>
                      ))}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#CBD5E1', marginBottom: '8px' }}>
                      📖 <strong>周期描述</strong>：{HISTORICAL_REPLAYS[state.stress.selectedReplayId]?.description}
                    </div>
                    {/* 回撤曲线预览 */}
                    <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', padding: '6px 0' }}>
                      {HISTORICAL_REPLAYS[state.stress.selectedReplayId]?.monthlyDrawdown.map((dd, idx) => (
                        <div key={idx} style={{ flex: '1', minWidth: '45px', textAlign: 'center', background: 'rgba(0,0,0,0.3)', padding: '4px 2px', borderRadius: '4px', fontSize: '0.7rem' }}>
                          <div style={{ color: '#94A3B8' }}>{idx + 1}月</div>
                          <div style={{ color: '#F87171', fontWeight: 600 }}>{(dd * 100).toFixed(0)}%</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 36 个月全量推演流水表格 (P0-1 & P2-5) */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div style={{ fontSize: '0.95rem', fontWeight: 700 }}>
                  📅 逐月资金流水推演表 ({showFullTimeline ? '展示全部 36 个月' : '展示前 12 个月'})
                </div>
                <button className="btn btn-outline btn-sm" onClick={() => setShowFullTimeline(!showFullTimeline)}>
                  {showFullTimeline ? '仅显示前 12 个月' : '展开显示全部 36 个月'}
                </button>
              </div>

              <div className="table-container" style={{ maxHeight: '550px', overflowY: 'auto' }}>
                <table>
                  <thead>
                    <tr>
                      <th>月份</th>
                      <th>期初缓冲池余额</th>
                      <th>当月分红到账</th>
                      <th>失业净收入缺口损耗</th>
                      <th>总生活支出</th>
                      <th>期末缓冲池余额</th>
                      <th>状态标识</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(showFullTimeline ? activeStressMetrics.timeline : activeStressMetrics.timeline.slice(0, 12)).map(row => {
                      const isUnemployed = row.unemploymentLoss > 0;
                      const isDeficit = row.endBuffer < 0;
                      let rowBg = 'transparent';
                      if (isDeficit) rowBg = 'rgba(239, 68, 68, 0.15)';
                      else if (isUnemployed) rowBg = 'rgba(245, 158, 11, 0.08)';

                      return (
                        <tr key={row.month} style={{ background: rowBg }}>
                          <td>第 {row.month} 个月 ({row.calendarMonth}月)</td>
                          <td>¥{row.startBuffer.toLocaleString()}</td>
                          <td style={{ color: '#38BDF8' }}>¥{row.dividend.toLocaleString()}</td>
                          <td style={{ color: isUnemployed ? '#FB7185' : '#94A3B8', fontWeight: isUnemployed ? 700 : 400 }}>
                            {isUnemployed ? `-¥${row.unemploymentLoss.toLocaleString()}` : '0'}
                          </td>
                          <td style={{ color: '#FBBF24' }}>-¥{row.withdraw.toLocaleString()}</td>
                          <td style={{ fontWeight: 700, color: row.endBuffer >= 0 ? '#34D399' : '#F87171' }}>
                            ¥{row.endBuffer.toLocaleString()}
                          </td>
                          <td>
                            {isDeficit ? (
                              <span className="tag tag-red">⚠️ 枯竭断流</span>
                            ) : (isUnemployed ? (
                              <span className="tag tag-yellow">失业期损耗</span>
                            ) : (
                              <span className="tag tag-green">正常平滑</span>
                            ))}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: 🌡️ 估值温度计与再平衡 (10指数 P2-1 & 增量再平衡 P2-2) */}
        {activeTab === 'thermometer' && (
          <div>
            <div className="card" id="thermometer-card">
              <div className="card-header">
                <div className="card-title">
                  <span>🌡️ 估值温度计与卖出侧纪律闭环 (10大核心指数监测)</span>
                  <span className="tag" style={{ background: thermometerMetrics.tier.color, color: '#FFF' }}>
                    {activeThermometerIndex.name}：{thermometerMetrics.tier.label} ({thermometerMetrics.percentile}%)
                  </span>
                </div>
                <span className="tag tag-blue">数据来源：本地基准缓存</span>
              </div>

              {/* 10大指数选择器与滑块 */}
              <div className="grid-2" style={{ gap: '16px', marginBottom: '18px' }}>
                <div className="form-group">
                  <label className="form-label">监测目标指数</label>
                  <select 
                    className="input-control"
                    value={state.thermometer.selectedIndex || 'H30269'}
                    onChange={e => setState({ ...state, thermometer: { ...state.thermometer, selectedIndex: e.target.value } })}
                  >
                    {THERMOMETER_INDICES.map(idx => (
                      <option key={idx.code} value={idx.code}>
                        {idx.name} ({idx.code}) - {idx.metricName}
                      </option>
                    ))}
                  </select>
                  <div style={{ fontSize: '0.75rem', color: '#94A3B8', marginTop: '4px' }}>
                    PE: {activeThermometerIndex.pe} | 股息率: {activeThermometerIndex.dividendYield}% | {activeThermometerIndex.desc}
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">
                    历史估值分位数调节：<strong>{thermometerMetrics.percentile}%</strong> (动态定投倍数: <strong style={{ color: '#10B981' }}>{thermometerMetrics.dcaMultiplier}x</strong>)
                  </label>
                  <input 
                    type="range" 
                    min="0" max="100" 
                    value={thermometerMetrics.percentile}
                    onChange={e => {
                      const p = parseInt(e.target.value) || 0;
                      setState({
                        ...state,
                        thermometer: {
                          ...state.thermometer,
                          percentileOverrides: {
                            ...state.thermometer.percentileOverrides,
                            [activeThermometerIndex.code]: p
                          }
                        }
                      });
                    }}
                    style={{ width: '100%', height: '8px', cursor: 'pointer' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#94A3B8', marginTop: '4px' }}>
                    <span>0% 深度低估</span>
                    <span>20% 低估</span>
                    <span>40% 中性</span>
                    <span>60% 偏热</span>
                    <span>80% 极度过热 100%</span>
                  </div>
                </div>
              </div>

              {/* 纪律指导与大额资金转入安全校验 (P2-1) */}
              <div style={{ background: 'rgba(255,255,255,0.04)', padding: '16px', borderRadius: '10px', border: `1px solid ${thermometerMetrics.tier.color}`, marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: thermometerMetrics.tier.color }}>
                    📢 当前状态操作纪律：{thermometerMetrics.tier.label}（定投步长放大系数: {thermometerMetrics.dcaMultiplier}x）
                  </div>
                  {thermometerMetrics.isDeepLow && (
                    <span className={`tag ${bufferMetrics.minBuffer >= 6 * (state.health.essentialMonthlyExpense || 12000) ? 'tag-green' : 'tag-yellow'}`}>
                      {bufferMetrics.minBuffer >= 6 * (state.health.essentialMonthlyExpense || 12000) ? '✅ 缓冲池超额充裕，允许大额加仓' : '⚠️ 缓冲池储备偏紧，禁止大额抽水！'}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '0.86rem', color: '#CBD5E1', lineHeight: '1.6' }}>
                  {thermometerMetrics.actionAdvice}
                </div>
                <div style={{ marginTop: '8px', fontSize: '0.82rem', color: '#FBBF24', fontWeight: 600 }}>
                  {thermometerMetrics.rebalanceAdvice}
                </div>
              </div>

              {/* P2-2: 持仓账本与估值温度计信号再平衡联动表 */}
              <div style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '10px' }}>
                ⚖️ 个人持仓账本与温度计再平衡联动提示表
              </div>
              <div className="table-container" style={{ marginBottom: '20px' }}>
                <table>
                  <thead>
                    <tr>
                      <th>代码</th>
                      <th>资产名称</th>
                      <th>对应参考指数</th>
                      <th>指数百分位</th>
                      <th>温度计信号</th>
                      <th>目标配置 (%)</th>
                      <th>当前市值 (万元)</th>
                      <th>实际占比 (%)</th>
                      <th>再平衡操作指引</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(state.board.assets).map(([code, asset]) => {
                      const holding = state.thermometer.userHoldings?.[code] ?? 10.0;
                      const targetIdxCode = asset.targetIndexCode || 'H30269';
                      const idxObj = THERMOMETER_INDICES.find(i => i.code === targetIdxCode) || THERMOMETER_INDICES[0];
                      const idxPercentile = (state.thermometer.percentileOverrides && state.thermometer.percentileOverrides[targetIdxCode] !== undefined) 
                        ? state.thermometer.percentileOverrides[targetIdxCode] 
                        : idxObj.defaultPercentile;
                      const sig = calculateThermometerSignal(idxPercentile);

                      const totalHolding = Object.values(state.thermometer.userHoldings || {}).reduce((a, b) => a + Number(b || 0), 0);
                      const currentPct = totalHolding > 0 ? (holding / totalHolding * 100) : 0;
                      const diffPct = currentPct - (asset.weight || 0);

                      return (
                        <tr key={code}>
                          <td><code>{code}</code></td>
                          <td><strong>{asset.name}</strong></td>
                          <td><span className="tag tag-blue">{idxObj.name}</span></td>
                          <td>{idxPercentile}%</td>
                          <td>
                            <span className="tag" style={{ background: sig.tier.color, color: '#FFF' }}>
                              {sig.tier.label}
                            </span>
                          </td>
                          <td>{asset.weight}%</td>
                          <td>
                            <input 
                              type="number"
                              className="input-control"
                              style={{ width: '80px', padding: '4px 8px' }}
                              value={holding}
                              step="1"
                              onChange={e => {
                                const val = parseFloat(e.target.value) || 0;
                                setState({
                                  ...state,
                                  thermometer: {
                                    ...state.thermometer,
                                    userHoldings: { ...state.thermometer.userHoldings, [code]: val }
                                  }
                                });
                              }}
                            />
                          </td>
                          <td>{currentPct.toFixed(1)}%</td>
                          <td>
                            {sig.isOverheated ? (
                              <span style={{ color: '#F87171', fontWeight: 600 }}>建议按月度 3 次分批将成长类持仓再平衡回目标权重</span>
                            ) : (sig.isDeepLow ? (
                              <span style={{ color: '#34D399', fontWeight: 600 }}>定投倍数放大 1.8x 建仓</span>
                            ) : (
                              <span style={{ color: '#94A3B8' }}>{diffPct > 3 ? `偏高 ${diffPct.toFixed(1)}%` : (diffPct < -3 ? `偏低 ${Math.abs(diffPct).toFixed(1)}%` : '持仓平衡')}</span>
                            ))}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* P2-2: 增量资金再平衡计算器 */}
              <div style={{ background: 'rgba(0,0,0,0.25)', padding: '16px', borderRadius: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38BDF8' }}>
                    💰 增量资金再平衡测算器 (不卖出持仓，仅以新增现金纠偏)
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <label style={{ fontSize: '0.8rem', color: '#94A3B8' }}>新增可用现金 (元):</label>
                    <input 
                      type="number"
                      className="input-control"
                      style={{ width: '130px', padding: '4px 8px' }}
                      value={state.thermometer.incrementalCapital || 50000}
                      step="10000"
                      onChange={e => setState({ ...state, thermometer: { ...state.thermometer, incrementalCapital: parseFloat(e.target.value) || 0 } })}
                    />
                  </div>
                </div>

                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>资产代码</th>
                        <th>资产名称</th>
                        <th>当前实际权重</th>
                        <th>目标权重</th>
                        <th>配置缺口状态</th>
                        <th>建议买入分配现金 (元)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {incrementalRebalance.allocations.map(a => (
                        <tr key={a.code}>
                          <td><code>{a.code}</code></td>
                          <td><strong>{a.name}</strong></td>
                          <td>{a.currentPct.toFixed(1)}%</td>
                          <td>{a.targetPct.toFixed(1)}%</td>
                          <td>
                            {a.diffPct < 0 ? (
                              <span className="tag tag-yellow">欠配 {Math.abs(a.diffPct).toFixed(1)}%</span>
                            ) : (
                              <span className="tag tag-green">足额</span>
                            )}
                          </td>
                          <td style={{ fontWeight: 700, color: a.allocatedCash > 0 ? '#34D399' : '#94A3B8' }}>
                            {a.allocatedCash > 0 ? `+¥${a.allocatedCash.toLocaleString()} 元` : '¥0'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: 📋 体检报告导出 */}
        {activeTab === 'report' && (
          <div>
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <span>📋 Markdown 体检报告实时导出 (全模块整合)</span>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button 
                    className="btn btn-outline btn-sm"
                    onClick={() => {
                      const md = generateMarkdownReport(state);
                      navigator.clipboard.writeText(md).then(() => {
                        setCopySuccess(true);
                        setTimeout(() => setCopySuccess(false), 2000);
                      });
                    }}
                  >
                    {copySuccess ? '✅ 已复制 Markdown' : '📋 复制报告文本'}
                  </button>
                  <button 
                    className="btn btn-primary btn-sm"
                    onClick={() => {
                      const md = generateMarkdownReport(state);
                      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.href = url;
                      link.download = `家庭财富规划量化体检报告_${new Date().toISOString().slice(0, 10)}.md`;
                      link.click();
                    }}
                  >
                    📥 下载 .md 报告
                  </button>
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '18px', borderRadius: '10px', maxHeight: '650px', overflowY: 'auto' }}>
                <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.82rem', color: '#E2E8F0' }}>
                  {generateMarkdownReport(state)}
                </pre>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* 目标编辑弹窗 */}
      {isModalOpen && editingGoal && (
        <div className="modal-backdrop">
          <div className="modal-box">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#FFF' }}>
                {state.goals.some(g => g.id === editingGoal.id) ? '✏️ 编辑规划目标' : '➕ 新增规划目标'}
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setIsModalOpen(false)}>✕</button>
            </div>

            <form onSubmit={handleSaveGoal}>
              <div className="form-group">
                <label className="form-label">目标名称</label>
                <input 
                  type="text" 
                  className="input-control" 
                  value={editingGoal.name}
                  placeholder="例如：2035 年子女教育金"
                  onChange={e => setEditingGoal({ ...editingGoal, name: e.target.value })}
                />
              </div>

              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">目标类型</label>
                  <select 
                    className="input-control"
                    value={editingGoal.type}
                    onChange={e => setEditingGoal({ ...editingGoal, type: e.target.value })}
                  >
                    {GOAL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">优先级</label>
                  <select 
                    className="input-control"
                    value={editingGoal.priority}
                    onChange={e => setEditingGoal({ ...editingGoal, priority: e.target.value })}
                  >
                    {GOAL_PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
              </div>

              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">目标金额 (元)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={editingGoal.targetAmount}
                    step="50000"
                    onChange={e => setEditingGoal({ ...editingGoal, targetAmount: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">目标时点年份</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={editingGoal.targetYear}
                    min="2026" max="2070"
                    onChange={e => setEditingGoal({ ...editingGoal, targetYear: parseInt(e.target.value) || 2026 })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">已单独预留金额 (元)</label>
                <input 
                  type="number" 
                  className="input-control" 
                  value={editingGoal.linkTo1To3y ? (state.health.bucket1To3y || 0) : (editingGoal.reservedAmount || 0)}
                  disabled={editingGoal.linkTo1To3y}
                  onChange={e => setEditingGoal({ ...editingGoal, reservedAmount: parseFloat(e.target.value) || 0 })}
                />
                <div style={{ marginTop: '6px' }}>
                  <label style={{ fontSize: '0.8rem', color: '#38BDF8', display: 'inline-flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                    <input 
                      type="checkbox" 
                      checked={editingGoal.linkTo1To3y}
                      onChange={e => setEditingGoal({ ...editingGoal, linkTo1To3y: e.target.checked })}
                    />
                    一键关联体检“未来 1-3 年确定要用的钱” (¥{(state.health.bucket1To3y || 0).toLocaleString()} 元)
                  </label>
                </div>
              </div>

              {/* 提前退休配置 */}
              {editingGoal.type === '提前退休' && (
                <div style={{ background: 'rgba(56, 189, 248, 0.08)', padding: '12px', borderRadius: '8px', marginBottom: '14px', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#38BDF8', marginBottom: '8px' }}>
                    🌴 退休支取参数设定
                  </div>
                  <div className="grid-3">
                    <div>
                      <label className="form-label">当前年龄</label>
                      <input 
                        type="number" 
                        className="input-control" 
                        value={editingGoal.retireConfig?.currentAge || 35}
                        onChange={e => setEditingGoal({
                          ...editingGoal,
                          retireConfig: { ...editingGoal.retireConfig, currentAge: parseInt(e.target.value) || 35 }
                        })}
                      />
                    </div>
                    <div>
                      <label className="form-label">计划退休年龄</label>
                      <input 
                        type="number" 
                        className="input-control" 
                        value={editingGoal.retireConfig?.retireAge || 50}
                        onChange={e => setEditingGoal({
                          ...editingGoal,
                          retireConfig: { ...editingGoal.retireConfig, retireAge: parseInt(e.target.value) || 50 }
                        })}
                      />
                    </div>
                    <div>
                      <label className="form-label">退休后月生活费 (元)</label>
                      <input 
                        type="number" 
                        className="input-control" 
                        value={editingGoal.retireConfig?.retireMonthlyExpense || 12000}
                        step="1000"
                        onChange={e => setEditingGoal({
                          ...editingGoal,
                          retireConfig: { ...editingGoal.retireConfig, retireMonthlyExpense: parseFloat(e.target.value) || 12000 }
                        })}
                      />
                    </div>
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                <button type="button" className="btn btn-outline" onClick={() => setIsModalOpen(false)}>取消</button>
                <button type="submit" className="btn btn-primary">保存规划目标</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 标的添加弹窗 (P0-4) */}
      {isAssetModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-box">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#FFF' }}>
                ➕ 添加自定义资产标的
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setIsAssetModalOpen(false)}>✕</button>
            </div>

            <form onSubmit={handleAddAsset}>
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">资产代码 (唯一识别)</label>
                  <input 
                    type="text" 
                    className="input-control" 
                    placeholder="如 510500" 
                    value={newAsset.code}
                    onChange={e => setNewAsset({ ...newAsset, code: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">标的名称</label>
                  <input 
                    type="text" 
                    className="input-control" 
                    placeholder="如 中证500 ETF" 
                    value={newAsset.name}
                    onChange={e => setNewAsset({ ...newAsset, name: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid-3">
                <div className="form-group">
                  <label className="form-label">所属资产桶</label>
                  <select 
                    className="input-control"
                    value={newAsset.bucket}
                    onChange={e => setNewAsset({ ...newAsset, bucket: e.target.value })}
                  >
                    <option value="safety">安全防御桶 (现金货币/短债)</option>
                    <option value="growth">长期成长桶 (红利核心/宽基)</option>
                    <option value="hedge">综合对冲桶 (黄金/长债)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">资产大类 (category)</label>
                  <select 
                    className="input-control"
                    value={newAsset.category}
                    onChange={e => setNewAsset({ ...newAsset, category: e.target.value })}
                  >
                    <option value="Equity">Equity (严格权益)</option>
                    <option value="FixedIncome">FixedIncome (防守固收)</option>
                    <option value="Cash">Cash (现金货币)</option>
                    <option value="Gold">Gold (黄金对冲)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">市场属性</label>
                  <select 
                    className="input-control"
                    value={newAsset.market}
                    onChange={e => setNewAsset({ ...newAsset, market: e.target.value })}
                  >
                    <option value="A股">A股</option>
                    <option value="港股">港股</option>
                    <option value="美股">美股</option>
                  </select>
                </div>
              </div>

              <div className="grid-3">
                <div className="form-group">
                  <label className="form-label">初始配置权重 (%)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={newAsset.weight}
                    step="1"
                    onChange={e => setNewAsset({ ...newAsset, weight: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">预期股息率 (%)</label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={newAsset.yield}
                    step="0.1"
                    onChange={e => setNewAsset({ ...newAsset, yield: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">风格特征</label>
                  <input 
                    type="text" 
                    className="input-control" 
                    value={newAsset.style}
                    onChange={e => setNewAsset({ ...newAsset, style: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                <button type="button" className="btn btn-outline" onClick={() => setIsAssetModalOpen(false)}>取消</button>
                <button type="submit" className="btn btn-primary">确认添加标的</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
