# D10 运维实战：自动化巡检与 Nginx 网关部署
上午（3h）：Shell 脚本与定时任务——cron 不是终端，它是另一个世界
第一块：建立心智模型（30分钟）—— 为什么 cron 是“另一个世界”？
很多新手会把脚本放进 crontab 后，发现报错了，甚至毫无反应。原因在于：你习惯的终端（Interactive Shell），和 cron 运行的环境（Non-Interactive Shell），是两个世界。
你现在打开 WSL 终端，敲下 echo $PATH，你会看到一长串路径。这是因为终端在启动时，读取了 ~/.bashrc、~/.profile 等配置文件，为你加载了环境变量。
但 cron 在后台唤醒时，是不加载这些配置文件的。 它的默认 PATH 通常只有 /usr/bin:/bin，而且它的工作目录是当前用户的根目录（~），不是你的项目目录。
面试级考点：
面试官：“为什么我的脚本在终端能跑，放进 cron 就提示 command not found 或 No such file or directory？”
你的回答：“因为 cron 执行时是非交互式 shell，不加载用户环境变量，且 PATH 极简。所以生产环境的脚本，第一原则是必须写绝对路径（无论是命令还是文件），并且要在脚本内显式地重定向日志，不能依赖终端输出。”

第二块：Shell 脚本骨架（60分钟）—— 写出“防弹”的巡检工具
我们不要去看几百页的 Shell 语法大全，直接写你巡检场景需要的：变量、函数、条件判断、循环、退出码。
1. 准备工作区
在终端里执行（注意用你真实的路径，假设你的项目在 /home/shenk/Project_A_V3）：
bash
# 进入 WSL 的你的项目目录
cd /home/shenk/Project_A_V3
# 建立脚本目录和日志目录
mkdir -p scripts
mkdir -p logs
# 创建今天的脚本文件
touch scripts/service_check.sh
chmod +x scripts/service_check.sh  # 必须给可执行权限
2. 编写“防弹”脚本
用 VS Code 打开这个 service_check.sh，我们把这段代码手敲一遍，我会逐行告诉你“为什么这么写”。
bash
#!/bin/bash
# 上面这行叫 Shebang，告诉系统用 bash 来跑，而不是用 sh（sh 没 bash 功能多）
﻿
# 【大厂标配三件套】
set -euo pipefail
# -e：遇到任何一条命令执行失败（退出码非0），立刻停止脚本，防止在错误的状态下继续执行！
# -u：如果使用了未定义的变量，立刻报错并退出。
# -o pipefail：如果一个管道命令（如 cmd1 | cmd2）中 cmd1 失败了，整个管道算失败。（默认情况下只看最后一条命令）
﻿
# 【定义常量（全大写）】
LOG_FILE="/home/shenk/Project_A_V3/logs/service_check.log"
# 面试细节：这里必须写绝对路径！因为 cron 不知道你的相对路径在哪。
﻿
# 【定义日志函数】
# local 关键字用来定义局部变量，防止变量名冲突污染全局
log() {
    local msg="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $msg" >> "$LOG_FILE"
}
﻿
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
﻿
# 【主逻辑】
log "========== 开始今日服务巡检 =========="
# 用循环批量处理，扩展性好
for svc in nginx cron; do
    check_service "$svc"
done
log "========== 服务巡检结束 =========="
3. 重点知识拆解（面试必问）：
local 的作用：如果没有 local，msg 和 svc 就成了全局变量。在大型脚本中，函数互相调用极易导致变量被覆盖（即“变量污染”）。
为什么用 systemctl is-active 而不是 ps aux | grep nginx？ ps 只能证明“系统里有个名字带 nginx 的进程”，如果是僵尸进程、或者配置错误导致进程挂起，ps 依然能查到。而 systemctl 是去问系统的服务管理器（systemd），它最清楚这个服务到底是不是健康。
WSL 特殊排雷：你在 WSL 里跑这个脚本，如果报 System has not been booted with systemd，是因为 WSL 默认没开 systemd。不要慌，这是环境问题，不是你的代码问题。你可以暂时在脚本里把 nginx cron 换成 ssh 或者任何你正在跑的进程，或者用 ps -ef | grep 进程名 替代。但在真实的云服务器上，systemctl 绝对是好使的。
﻿
4. 运行测试
在终端执行：
bash
./scripts/service_check.sh
然后看看日志：
bash
cat logs/service_check.log
确保你看到了时间戳和结果。如果顺利，手敲代码并跑通，上午的第一个产出物就诞生了。
﻿
第三块：crontab 安全写法（60分钟）—— 给脚本装上定时器
脚本能跑了，现在我们要让它在每天凌晨 2:30 自动跑。很多新手直接写个 30 2 * * * 就完事了，但在生产环境，这叫“裸奔”。
1. 认识 Crontab
bash
crontab -e  # 编辑当前用户的定时任务
crontab -l  # 查看当前用户有哪些定时任务
五个星号的含义：分 时 日 月 周。
30 2 * * * 就是每天凌晨 2 点 30 分。
﻿
2. 从“裸奔”到“生产级”
你先看看这个能跑，但极其危险的写法：
bash
30 2 * * * /home/shenk/Project_A_V3/scripts/service_check.sh >> /home/shenk/Project_A_V3/logs/cron.log 2>&1
危险1：没有指定解释器，系统可能用 sh 去跑你的 bash 脚本。
危险2：没有防重叠机制。如果脚本卡死了，第二天 2:30 又启动了一个，堆积起来会把服务器内存吃光。
危险3：>> 重定向必须有，因为 cron 的输出默认通过邮件发给 root，但很多服务器没配邮件服务，你根本不知道跑没跑。2>&1 表示把错误输出也重定向到同一个日志文件里。
大厂生产级写法（请把这行原封不动复制进 crontab -e 中）：
bash
30 2 * * * flock -n /tmp/service_check.lock /bin/bash /home/shenk/Project_A_V3/scripts/service_check.sh >> /home/shenk/Project_A_V3/logs/cron.log 2>&1
核心知识点：flock -n
flock 是文件锁。它会在 /tmp/service_check.lock 创建一个锁文件。
-n 代表 --nonblock（非阻塞）。意思是：如果上一次任务还没跑完，锁还没释放，这次的定时任务直接放弃执行并退出。这就彻底杜绝了任务重叠把机器卡死的问题。
﻿
3. 如何验证 cron 真的在跑？
你不可能等到明天凌晨 2:30 去验证。测试方法是：把 30 2 * * * 改成 * * * * *（每分钟跑一次），保存退出。然后去干别的，等两分钟。
查看日志：
bash
tail -f /home/shenk/Project_A_V3/logs/cron.log
如果你看到了报错，比如 Permission denied 或者找不到命令，这就是因为 cron 那个“另一个世界”的环境问题。你需要根据报错去修脚本（比如把 date 命令改成绝对路径 /usr/bin/date，或者统一在脚本头部重新声明 PATH）。
测试成功后，一定要记得 crontab -e 把它改回 30 2 * * *。
下午（4h）：网络排障分层 + Nginx 反向代理与日志切割
第一部分：网络排障——按层“剥洋葱”（90分钟）
面试官问：“网站打不开你怎么查？”新手会直接瞎重启，老手会按四层模型，从外到内，用工具一步步缩小范围。
1. 搭建“案发现场”（15分钟）
我们要排障，得先有个靶机。在 WSL 终端里，我们用 Python 自带的模块起一个最简单的 Web 服务：
bash
# 进入你的项目目录
cd ~/Project_A_V3
# 启动一个监听在 8000 端口的 HTTP 服务
python3 -m http.server 8000
（注意：这个终端会挂起，代表服务正在运行。请在 VS Code 终端右上角点 + 号，新建一个终端窗口来进行后面的操作。）
2. 四层排查演练（45分钟）
第一层：DNS 解析
* 现象：你不知道这个域名指向哪里。
* 命令：dig +short api.deepseek.com
* 面试考点：+short 只输出最终 IP。如果不加，你会看到 ANSWER SECTION，你能看到 TTL（缓存时间）。如果解析不对，去查 /etc/hosts 是不是被劫持了，或者查 /etc/resolv.conf 看用的哪个 DNS 服务器。
第二层：连通性
* 现象：知道 IP 了，不知道网络通不通。
* 命令：ping -c 4 127.0.0.1 （-c 4 代表只发4个包就停）。
* 面试考点：千万不要以为 ping 通了服务就没问题！ ping 走的是 ICMP 协议，你的 Web 服务走的是 TCP 协议。服务器防火墙经常允许 ICMP，但拦截 TCP 端口。
第三层：端口与连接（核心排查）
* 现象：网络通了，但服务连不上。
* 命令：ss -tulnp | grep 8000
* 面试考点：面试官最爱问 ss。
-t TCP，-u UDP，-l 处于 LISTEN（监听）状态，-n 不解析域名（快），-p 显示进程 PID。
重点：看 Local Address 是 0.0.0.0:8000 还是 127.0.0.1:8000。如果是 127.0.0.1，说明只有本机能访问，外网进不来；如果是 0.0.0.0，说明所有网卡都在听。
进阶：面试官会问 TIME_WAIT 状态太多怎么办？答：说明主动关闭连接方太多，可以调整内核参数（如 tcp_tw_reuse）。
第四层：应用与 HTTP 层
* 现象：端口在听，但网页打开慢或者报错。
* 命令：curl -o /dev/null -s -w "dns:%{time_namelookup} tcp:%{time_connect} tls:%{time_appconnect} first_byte:%{time_starttransfer} total:%{time_total}\n" http://127.0.0.1:8000/
* 面试考点：这行命令是神技。面试官问你“页面加载慢，是网络慢还是服务器处理慢？”你用这行命令就能证明：
如果 dns 耗时长，说明域名解析慢。
如果 tcp 耗时长，说明网络握手慢。
如果 first_byte 慢，说明后端 Python/Java 处理逻辑卡住了。
* 抓包排雷：sudo tcpdump -i any port 8000 -nn -s0 -c 20
-i any：所有网卡；-nn：不把 IP 解析成主机名（快）；-s0：抓完整数据包；-c 20：抓 20 个就停。
3. 制造故障并记录（30分钟）
* 去挂起 http.server 的终端按 Ctrl+C 停掉服务。
* 在新终端用 curl -v http://127.0.0.1:8000/（你会发现报错 Connection refused）。
* 用 ss -tulnp | grep 8000（你会发现端口消失了）。
* 你的交付物：新建一个 docs/D10_network_troubleshoot.md 文件，把这三个现象（停掉服务 -> curl 报错 -> ss 找不到端口）的截图或文字记录下来，这就是你的排障档案。
第二部分：Nginx 反向代理与日志切割（150分钟）
现在我们有了 8000 端口的 Python 服务，我们要给它穿上“防弹衣”——Nginx。
1. 为什么需要反向代理？（10分钟）
* 正向代理：替客户端翻墙（客户端知道最终去哪）。
* 反向代理：替服务器挡子弹（客户端以为 Nginx 就是服务器，其实 Nginx 在背后把请求转给了 8000 端口的 Python）。Nginx 可以处理 HTTPS、做限流、做负载均衡。
2. 安装与配置 Nginx（50分钟）
1. 停掉刚才的 Python 服务，在后台启动一个（加上 & 符号）：
bash
python3 -m http.server 8000 &
1. 在 WSL 安装 Nginx：
bash
sudo apt update
sudo apt install nginx -y
sudo service nginx start
（验证：在浏览器里访问 http://localhost:80，看到 Welcome to nginx 就成功了）。
1. 配置反向代理：编辑配置文件：
bash
sudo nano /etc/nginx/sites-available/default
找到 location / { ... } 那一块，把它改成：
nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
（原理解析：X-Real-IP 和 X-Forwarded-For 是把真实的客户端 IP 传给后端。不然你的 Python 服务日志里，所有的访问者 IP 都会变成 127.0.0.1，因为请求是 Nginx 转发过来的。）
1. 测试配置并平滑重启：
bash
sudo nginx -t   # 测试语法有没有错
sudo nginx -s reload   # 不打断服务，重新加载配置
1. 在浏览器里访问 http://localhost，你会发现，看到的是你的 Python http.server 的目录列表。反向代理成功！
3. 日志切割（90分钟——大厂重点排障场景）
Nginx 每天都在写日志（/var/log/nginx/access.log）。如果不切割，半年后这个文件会变成几十个 G，磁盘就爆了。Linux 自带了切肉机：logrotate。
1. 查看 Nginx 的日志切割配置：
bash
cat /etc/logrotate.d/nginx
1. 面试核心原理解析：
text
/var/log/nginx/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        invoke-rc.d nginx rotate >/dev/null 2>&1
    endscript
}
daily：每天切一次。
rotate 30：保留最近 30 天的，老的删掉。
compress：把旧日志用 gzip 压缩（省空间）。
致命面试题：为什么要执行 postrotate 里的东西？
答：Linux 里文件是通过 inode 寻址的。日志切割实际上是把 access.log 重命名成了 access.log.1。Nginx 默认是一直往旧的那个 inode 里写。如果不告诉 Nginx 重新打开文件（reopen），新的 access.log 就永远是空的，而重命名后的 access.log.1 会被 Nginx 继续撑爆。
1. 强制切割实战（验证奇迹）：不要等到明天，直接强制让 logrotate 跑一次：
bash
sudo logrotate -vf /etc/logrotate.d/nginx
# -v 显示详细过程，-f 强制立刻切割
切完之后，去 ls -l /var/log/nginx/，你会发现多了 .1 或 .gz 结尾的文件，而且新的 access.log 生成了。
傍晚（2h）：八股与文档——把今天做的事翻译成面试语言
今天的八股不要泛泛刷。只刷和 D10 直接相关、并且面试官会追着问的题：
1. cron 相关（口述 2 分钟）
* crontab 五个字段分别是什么？*/5 * * * * 和 5 * * * * 有什么区别？
* 为什么终端能跑、cron 跑不了？至少说出三个原因。
* 怎么防止 cron 任务重叠？flock 和“脚本内检查进程”各有什么取舍？
2. 网络排障（口述 2 分钟）
* 用户说“网站打不开”，你的排查顺序是什么？按 DNS → 连通性 → 端口 → HTTP 四层说。
* ping 通但端口不通，可能是什么问题？
* ss 和 netstat 的区别？TIME_WAIT 过多怎么处理？
* tcpdump 为什么要先过滤再抓？-nn 和 -s0 分别是什么作用？
3. HTTP / Nginx（口述 2 分钟）
* 502 和 504 的区别？分别更可能是哪一层的问题？
* 反向代理为什么要设 X-Forwarded-For？不设会怎样？
* Nginx 日志切割后为什么需要 reopen？
文档任务： 把今天的 service_check.sh、crontab 行、Nginx 配置、logrotate 配置、排障记录整理进 Project_A_V3/README.md 或单独的 D10_ops_runbook.md。大厂培训模式里，运维能力的证据不是“我学过”，是“我有 runbook，别人能照着复现”。
