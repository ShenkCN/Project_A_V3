#!/bin/bash
# 上面这行叫 Shebang，告诉系统用 bash 来跑，而不是用 sh（sh 没 bash 功能多）

# 【大厂标配三件套】
set -euo pipefail
# -e：遇到任何一条命令执行失败（退出码非0），立刻停止脚本，防止在错误的状态下继续执行！
# -u：如果使用了未定义的变量，立刻报错并退出。
# -o pipefail：如果一个管道命令（如 cmd1 | cmd2）中 cmd1 失败了，整个管道算失败。（默认情况下只看最后一条命令）

# 【定义常量（全大写）】
LOG_FILE="/home/shenk/Project_A_V3/logs/service_check.log"
# 面试细节：这里必须写绝对路径！因为 cron 不知道你的相对路径在哪。

# 【定义日志函数】
# local 关键字用来定义局部变量，防止变量名冲突污染全局
log() {
    local msg="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $msg" >> "$LOG_FILE"
}

# 【定义检查服务函数】
check_service() {
    local svc="$1"
    # 2>/dev/null 表示把错误输出丢掉，避免屏幕上出现一堆报错
    # is-active --quiet 不会输出 "active" 字样，只通过退出码（0成功，非0失败）来表达状态
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        log "OK   $svc is active"
    else
        log "FAIL $svc is not active"
        # 这里其实还可以加一个发送告警的动作，我们后面 Day 11/12 再扩展
    fi
}

# 【主逻辑】
log "========== 开始今日服务巡检 =========="
# 用循环批量处理，扩展性好
for svc in nginx cron; do
    check_service "$svc"
done
log "========== 服务巡检结束 =========="