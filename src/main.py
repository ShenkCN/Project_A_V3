import os
import sys
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor
from src.logger import get_logger
from src.notifier import Notifier

log = get_logger("Main")

def get_project_root() -> str:
    """获取项目根目录（V3）的绝对路径"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="智能日志巡检与并发告警 v3")
    parser.add_argument("--log_file", type=str, default="app.log", help="巡检日志路径")
    parser.add_argument("--rules", type=str, default="ERROR,timeout,OOM", help="巡检规则")
    return parser.parse_args()

def load_config() -> dict:
    config_path = os.path.join(get_project_root(), "config", "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        log.error(f"配置文件不存在: {config_path}")
        sys.exit(1)

def scan_log(file_path: str, rules: list[str]) -> list[str]:
    alerts = []
    full_path = os.path.join(get_project_root(), file_path)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                for rule in rules:
                    if rule.lower() in line.lower():
                        alerts.append(line)
                        break  # 核心修复：命中一个就跳出，防重复
    except FileNotFoundError:
        log.error(f"找不到日志文件: {full_path}")
        return []
    return alerts

def main() -> None:
    args = parse_args()
    config = load_config()
    rules = [r.strip() for r in args.rules.split(",") if r.strip()]
    channels = config.get("channels", ["钉钉"])

    log.info(f"--- 开始巡检日志: {args.log_file} ---")
    alerts = scan_log(args.log_file, rules)

    if not alerts:
        log.info("✅ 日志正常，未发现异常。")
        return

    log.warning(f"⚠️ 共发现 {len(alerts)} 条异常，准备并发告警...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=len(channels)) as pool:
        for channel in channels:
            notifier = Notifier(channel)
            pool.submit(notifier, f"发现 {len(alerts)} 条异常，最后一条为: {alerts[-1]}")
            
    log.info(f"--- 告警发送完毕，耗时: {time.time() - start_time:.2f} 秒 ---")

if __name__ == "__main__":
    main()