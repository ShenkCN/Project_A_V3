# Day 9 运维基础：Linux 核心命令与系统排障
Project_A_V3的目录结构：
Project_A_V3/
├── config/
│   └── config.json      # 规则与告警渠道配置
├── logs/                # 运行日志存放目录（自动切割）
├── src/                 # 核心源码
│   ├── __init__.py
│   ├── logger.py        # 日志封装组件
│   ├── notifier.py      # 告警发送组件
│   ├── main.py          # 应用日志巡检入口
│   └── system_audit.py  # 系统底层审计入口
├── tests/               # 单元测试
│   ├── __init__.py
│   └── test_main.py
├── requirements.txt     # 依赖清单
└── README.md

1102D9全流程命令速查表
1,以管理员身份打开 PowerShell，在开始菜单搜索“PowerShell”，右键选择“以管理员身份运行”。
2,wsl --install -d Ubuntu-22.04安装第一次重启后再安装一次
3,账号shenk密码shenk
4,一键换成阿里云源sudo sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && sudo sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && sudo apt update
5,在 VS Code 左侧扩展搜 WSL 并安装。装完后，看 VS Code 左下角有个蓝色的 >< 图标，点它，选择 Connect to WSL
6. 更新软件包列表、 安装 python3-venv 和 python3-pip、创建虚拟环境venv、激活虚拟环境
sudo apt update
sudo apt install python3.10-venv python3-pip
python3 -m venv venv
source venv/bin/activate
(敲完这行，你会发现终端最前面多了一个 (venv)。注意：Linux 激活环境的命令和 Windows 不一样，这里是 source)
7. 安装依赖
echo "pytest" > requirements.txt
echo "pytest-cov" >> requirements.txt
pip install -r requirements.txt
(因为你建了新的虚拟环境，所以得重新装一遍
3. 造假日志数据
echo "INFO 正常启动" > app.log
echo "ERROR 数据库挂了" >> app.log
echo "timeout API超时" >> app.log
4. 运行系统巡检脚本（D9 的绝对核心！）(需提前创建Project_A_V3)
python -m src.system_audit
预期你会看到：打印出磁盘使用率，并且由于代码里 Popen 了一个 sleep 1000，它会立刻找到并 kill -9 掉这个进程。这证明了你的 Python 代码正在操控 Linux 系统的底层！
5. 跑通主程序和自动化测试
bash
python -m src.main --log_file app.log
python -m pytest -v
预期：主程序会并发发送 3 个渠道的告警。测试会显示 3 passed。


📁 1. 文件 (Files)：一切皆文件
Linux 的设计哲学是“一切皆文件”，连硬件设备（如硬盘、网卡）在 /dev 目录下都是文件。
* 核心命令：ls -l (查看详细信息)、cd (切换)、pwd (当前位置)、touch (创建)、rm (删除，慎用 -rf)、cp/mv (复制/移动)。
* 大厂考点：
隐藏文件以 . 开头（如 .gitignore、.bashrc）。
软链接 vs 硬链接：软链接类似 Windows 的快捷方式，原文件删了它就失效；硬链接相当于给同一个文件起了多个名字，删掉一个另一个还在。命令：ln -s 源文件 软链接名。
🔐 2. 权限 (Permissions)：系统安全的底线
在 ls -l 的输出中，第一列就是权限，例如 -rw-r--r--。
* 字母含义：r 读(4)、w 写(2)、x 执行(1)、- 无(0)。
* 三组权限：属主(User)、属组(Group)、其他用户(Others)。
* 核心命令：
chmod 600 file：只有自己能读写（你昨天存放 API Key 的神仙操作）。6 = 4(读) + 2(写)。
chmod +x script.sh：给脚本加上可执行权限。
chown user:group file：修改文件的归属。
* 大厂考点：为什么 .pem 私钥文件必须是 600 权限？因为如果别的用户能读，你的服务器就被盗了。SSH 登录时如果私钥权限过大，系统会直接拒绝你登录。
⚙️ 3. 进程 (Processes)：谁在吃我的 CPU？
程序一跑起来，就成了进程。大厂运维每天都要看服务器是不是被某个进程“卡死”了。
* 核心命令：
ps aux：静态查看所有进程。重点看 PID（进程号）、%CPU、%MEM，以及 STAT 状态列。
top：动态实时监控（类似 Windows 任务管理器）。
kill -9 PID：强制击杀进程。
* 大厂考点（面试必问）：
D 状态（Uninterruptible Sleep）：不可中断睡眠。通常是因为进程在等磁盘 I/O（比如硬盘快坏了）。它连 kill -9 都杀不死，只能等 I/O 超时或重启机器。
僵尸进程（Zombie，Z 状态）：子进程死了，但父进程没管它（没回收）。僵尸进程杀不掉，只能杀掉它的父进程。
🛠️ 4. systemd：服务的大管家
在真实的生产环境（CentOS/Ubuntu）里，你的 Python 脚本不是用 python main.py 跑的，而是被封装成了系统服务，由 systemd 接管。
* 核心命令：
systemctl start/stop/restart nginx：启动/停止/重启服务。
systemctl enable nginx：设置开机自启（很重要！服务器重启后服务要自己爬起来）。
systemctl status nginx：排障第一命令。看服务是否 active (running)，最后一行经常直接告诉你报错原因。
* 你在 WSL 遇到坑的原因：WSL 默认为了轻量，没有启动 systemd 作为 1 号进程，所以你敲 systemctl 会报错。但在云服务器上，它绝对是老大。
📄 5. journalctl：排障的终极日志
既然服务归 systemd 管，那服务产生的日志自然也归它管。journalctl 就是查看 systemd 日志的神器。
* 核心命令：
journalctl -u nginx：查看指定服务（-u 代表 unit）的日志。
journalctl -p err：只看错误级别（error）的日志（按级别过滤）。
journalctl --since "10 min ago" 或 --since today：按时间过滤。排查突发故障时，时间窗口是最重要的。
journalctl -f：实时滚动（类似 tail -f）。
🚨 大厂面试实战模拟：一条线的排障思路
面试官：“Shenk，假设线上一个负责处理用户数据的 Python 服务突然挂了，访问报 502，你现在登录到了这台服务器，你敲什么命令？”
你的满分回答（串联五大考点）：1. 查服务状态：首先敲 systemctl status user_data.service。如果看到 inactive (dead)，说明程序挂了；如果是 failed，看它给的提示。
2. 查日志：接着敲 journalctl -u user_data.service --since "10 min ago" -p err。看最近10分钟有没有抛出 Python 异常（比如内存溢出、连接数据库失败）。
3. 查系统资源：如果日志里没明显报错，敲 df -h 看看是不是磁盘满了（日志写不进去导致崩溃）；敲 top 或 free -h 看看是不是内存被吃光了，触发了系统的 OOM Killer（OOM 会直接杀进程）。
4. 查权限：如果日志报 Permission denied，用 ls -l 看看是不是运行这个服务的用户，没有权限读取某个配置文件。
5. 重启与恢复：如果修复了配置，敲 systemctl restart user_data.service，然后再次 status 确认变绿。
