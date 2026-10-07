#!/usr/bin/env python3
"""可靠执行行情、分红与回测更新，供 GitHub Actions 和本地手动调用。"""

import argparse
import copy
import json
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
LIVE_DATA_PATH = PROJECT_ROOT / "live_data.json"
PRESETS_PATH = PROJECT_ROOT / "strategy_presets.json"


def run_with_retry(command, attempts=3, base_delay=20, runner=subprocess.run, sleeper=time.sleep):
    """执行命令并按线性退避重试；全部失败时保留原始退出码。"""
    if attempts < 1:
        raise ValueError("attempts 必须至少为 1")
    if base_delay < 0:
        raise ValueError("base_delay 不能为负数")

    last_result = None
    for attempt in range(1, attempts + 1):
        print(f"[scheduled-update] 第 {attempt}/{attempts} 次执行：{' '.join(command)}", flush=True)
        last_result = runner(command, cwd=PROJECT_ROOT)
        if last_result.returncode == 0:
            return last_result
        if attempt < attempts:
            delay = base_delay * attempt
            print(f"[scheduled-update] 执行失败，{delay} 秒后重试。", flush=True)
            sleeper(delay)

    raise subprocess.CalledProcessError(last_result.returncode, command)


def restore_if_only_metadata_changed(path, original_text, metadata_path):
    """若仅运行时间变化，则恢复原文件，避免补跑制造无意义提交。"""
    if original_text is None or not path.exists():
        return False
    try:
        before = json.loads(original_text)
        after = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False

    def without_metadata(payload):
        normalized = copy.deepcopy(payload)
        parent = normalized
        for key in metadata_path[:-1]:
            parent = parent.get(key) if isinstance(parent, dict) else None
            if parent is None:
                return normalized
        if isinstance(parent, dict):
            parent.pop(metadata_path[-1], None)
        return normalized

    if without_metadata(before) != without_metadata(after):
        return False
    path.write_text(original_text, encoding="utf-8")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="更新公开行情、现金分配数据与策略回测")
    parser.add_argument("--attempts", type=int, default=3, help="每个联网步骤的最大尝试次数")
    parser.add_argument("--base-delay", type=int, default=20, help="重试线性退避的基础秒数")
    args = parser.parse_args(argv)

    python = sys.executable
    original_live = LIVE_DATA_PATH.read_text(encoding="utf-8") if LIVE_DATA_PATH.exists() else None
    original_presets = PRESETS_PATH.read_text(encoding="utf-8") if PRESETS_PATH.exists() else None
    run_with_retry([python, "update_data.py"], args.attempts, args.base_delay)
    run_with_retry([python, "backtest.py"], args.attempts, args.base_delay)

    live_unchanged = restore_if_only_metadata_changed(
        LIVE_DATA_PATH, original_live, ("data_quality", "generated_at")
    )
    backtest_unchanged = restore_if_only_metadata_changed(
        PRESETS_PATH, original_presets, ("backtest", "generated_at")
    )
    if live_unchanged:
        print("[scheduled-update] 行情与现金分配无实质变化，保留原生成时间。", flush=True)
    if backtest_unchanged:
        print("[scheduled-update] 回测结果无实质变化，保留原生成时间。", flush=True)

    # 更新完成后必须通过结构、覆盖范围、新鲜度和回测对齐检查，失败则禁止提交。
    subprocess.run(
        [python, "tests/data_integrity_check.py"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    print("[scheduled-update] 数据更新、回测与完整性检查全部通过。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
