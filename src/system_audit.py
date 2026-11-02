import subprocess
import time
from src.logger import get_logger

log = get_logger("SystemAudit")

def check_disk_usage():
    """检查磁盘使用率（运维巡检核心指标）"""
    try:
        # 调用 Linux 命令 df -h 查看磁盘
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            usage_str = lines[1].split()[4] # 比如 '15%'
            usage = int(usage_str.strip('%'))
            if usage > 80:
                log.warning(f"⚠️ 磁盘告警！当前使用率: {usage}%")
            else:
                log.info(f"✅ 磁盘正常，使用率: {usage}%")
    except Exception as e:
        log.error(f"执行 df 命令失败: {e}")

def kill_zombie_process(process_name: str):
    """查找并杀掉卡死的进程"""
    result = subprocess.run(["pgrep", process_name], capture_output=True, text=True)
    pids = result.stdout.strip().split()
    
    if not pids:
        log.info(f"没有找到名为 {process_name} 的进程。")
        return

    for pid in pids:
        log.warning(f"🔪 发现进程 {process_name} (PID: {pid})，正在强制击杀...")
        subprocess.run(["kill", "-9", pid])
        log.info(f"进程 {pid} 已清理。")

if __name__ == "__main__":
    log.info("--- 启动系统巡检 ---")
    check_disk_usage()
    
    log.info("模拟启动一个卡死的 sleep 1000 进程...")
    subprocess.Popen(["sleep", "1000"])
    time.sleep(1) 
    kill_zombie_process("sleep")