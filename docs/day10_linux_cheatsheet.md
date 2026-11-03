# D10 运维实战：自动化巡检与 Nginx 网关部署

📁 A. 工作区准备
1. 进入项目目录并创建标准结构：为什么建两个文件夹？为了规范。scripts 专放脚本，logs 专放输出日志。
cd /home/shenk/Project_A_V3
mkdir -p scripts logs
touch scripts/service_check.sh
chmod +x scripts/service_check.sh
(敲完 chmod 这行，你的脚本就有了执行权限，否则待会 cron 跑的时候会报 Permission denied。)
📝 B. 编写巡检脚本（service_check.sh）
1. 编写防弹脚本：用 VS Code 打开 scripts/service_check.sh，写入以下代码。为什么要加 set -euo pipefail？为了防雷。一旦脚本内出现报错（比如命令找不到），立刻停止，绝不带病往下跑。为什么用 systemctl is-active 而不是 ps？因为 ps 只能看到名字，而 systemctl 问的是系统服务管家，状态最准。
#!/bin/bash
set -euo pipefail
LOG_FILE="/home/shenk/Project_A_V3/logs/service_check.log"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG_FILE"; }

check_service() {
    local svc="$1"
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        log "OK   $svc is active"
    else
        log "FAIL $svc is not active"
    fi
}

for svc in nginx cron; do check_service "$svc"; done
🚀 C. 手动运行验证（排雷第一步）
1. 手动跑通再谈自动化：永远不要在没跑通脚本的情况下直接扔给 cron。
./scripts/service_check.sh
cat logs/service_check.log
预期结果：终端不会有输出，但 cat 会看到 logs/service_check.log 里写入了类似 [2026-11-03 09:13:36] OK cron is active 的日志。如果这步报错，说明脚本写错了，后面配 cron 也是白搭。
⏱️ D. 写入 crontab（生产级定时任务）
1. 编辑定时任务：
crontab -e
1. 写入防重叠命令：在打开的 nano 编辑器中，输入以下代码并保存退出（Ctrl+O -> 回车 -> Ctrl+X）。为什么要用 flock -n？因为 cron 是非交互环境，如果脚本卡死，下次又启动，会把机器资源吃光。flock 就是一把锁，拿不到锁直接退出，绝不排队。为什么要用绝对路径 /usr/bin/flock 和 /bin/bash？因为 cron 的 PATH 极简，不认系统环境变量。
30 2 * * * /usr/bin/flock -n /tmp/service_check.lock /bin/bash /home/shenk/Project_A_V3/scripts/service_check.sh >> /home/shenk/Project_A_V3/logs/cron.log 2>&1
1. 验证 cron 服务是否活着：
sudo service cron start
ps aux | grep cron
预期结果：能看到 root ... /usr/sbin/cron -f 的进程。如果是 WSL，经常会休眠导致 cron 没启动，这一步必不可少。
1. 查看系统日志（案发现场）：如果 cron 没反应，看这个日志最准。
grep CRON /var/log/syslog | tail -n 10
🌐 E. 启动后端 Python 服务
1. 启动后台服务：为什么末尾加 &？因为不加 &，终端会被这个服务锁死，你没法敲其他命令。加了 &，服务在后台默默跑。
python3 -m http.server 8000 &
curl -I http://127.0.0.1:8000
预期结果：curl -I 应该返回 HTTP/1.0 200 OK。
🕵️ F. 网络排障命令（四层剥洋葱）
1. DNS 解析：
dig +short api.deepseek.com
(预期：直接输出两个 IP，说明 DNS 没问题。)
1. 连通性：
ping -c 4 127.0.0.1
(预期：4个包全通，0% packet loss。)
1. 端口与服务：
ss -tulnp | grep 8000
(预期：看到 0.0.0.0:8000 或 127.0.0.1:8000，后面跟着 python3 的进程。如果没输出，说明服务挂了。)
1. HTTP 分段耗时：
curl -o /dev/null -s -w "dns:%{time_namelookup} tcp:%{time_connect} total:%{time_total}\n" http://127.0.0.1:8000/
(预期：输出各阶段的毫秒数。如果 first_byte 很大，说明服务处理慢；如果 tcp 大，说明网络握手慢。)
1. 抓包（需开两个终端）：终端A开着听，终端B去发请求。终端A：sudo tcpdump -i any port 8000 -nn -s0 -c 20终端B：curl -v http://127.0.0.1:8000/(预期：终端A会刷出 TCP 三次握手和 HTTP GET 的包。)
🛡️ G. 安装并配置 Nginx 反向代理
1. 安装与启动：
sudo apt update
sudo apt install nginx -y
sudo service nginx start
(预期：浏览器访问 http://localhost 能看到紫色的 Nginx 欢迎页。)
1. 配置反向代理：
sudo nano /etc/nginx/sites-available/default
把 location / { ... } 里面的 try_files 删掉，换成：
nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
(为什么要加这几行 proxy_set_header？因为代理后，后端只能看到 127.0.0.1，必须用 Header 把真实客户端 IP 传过去，否则后端日志全是代理的 IP，风控就瞎了。)
1. 检查与平滑重载：先 nginx -t 测语法，没问题再 reload，不能直接重启，防止把线上的其他服务搞断。
sudo nginx -t
sudo nginx -s reload
预期结果：刷新浏览器 http://localhost，看到的不是 Nginx 欢迎页了，而是你 Python 目录的文件列表，说明反向代理打通。
📄 H. 日志切割验证
1. 看默认配置：
cat /etc/logrotate.d/nginx
(注意看 postrotate 里面的东西，它是用来让 Nginx 重新打开新日志文件的。)
1. 强制切割演练：-f 是强制立刻执行，-v 是打印详细过程。
sudo logrotate -vf /etc/logrotate.d/nginx
ls -l /var/log/nginx/
预期结果：你能看到 /var/log/nginx/ 下多了一个 access.log.1（或者被压缩的 .gz），并且全新的 access.log 生成了。说明切割成功。


1. 运维速查表（Cheat Sheet）
- **Cron 防重叠**：`flock -n /tmp/task.lock /path/to/script.sh`
- **排查 DNS**：`dig +short 域名`
- **排查端口**：`ss -tulnp | grep 端口号`
- **分析 HTTP 耗时**：`curl -o /dev/null -s -w "dns:%{time_namelookup} tcp:%{time_connect} total:%{time_total}\n" URL`
- **强制切割日志**：`logrotate -vf /etc/logrotate.d/nginx`
- **Nginx 平滑重载**：`nginx -t` 检查语法，`nginx -s reload` 生效。
2. 自动化巡检脚本 (service_check.sh)
- 脚本核心逻辑：使用了 `set -euo pipefail`，并用 `systemctl is-active --quiet` 检查服务。
- 调度配置 (crontab)：
  ```bash
  30 2 * * * flock -n /tmp/service_check.lock /bin/bash /home/shenk/Project_A_V3/scripts/service_check.sh >> /home/shenk/Project_A_V3/logs/cron.log 2>&1
3.Nginx反向代理配置
将 80 端口请求转发至 8000 端口的 Python 服务。
配置片段：
nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
4.故障排障记录（Troubleshooting）
* 故障场景 1（DNS/网络）：[记录你用 dig 和 ping 测试的过程]
* 故障场景 2（端口未监听）：主动停掉 Python 服务，执行 ss -tulnp | grep 8000 发现无输出，curl 报 Connection refused。
* 故障场景 3（抓包分析）：使用 tcpdump 验证了 TCP 的三次握手包。
