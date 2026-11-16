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