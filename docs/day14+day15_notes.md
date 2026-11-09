🚀 D14 + D15 总结：从“手工敲命令”到“系统服务化”，在真实报错中打通交付闭环
🎯 一、 战果清单（产出物）
这两天是整个转型计划中“最硬核”的实操场，彻底把之前散落的 Python 和 Linux 知识，组装成了能在生产环境跑起来的“服务”。
1. D14 产出：
Shell 武器库：熟练使用 grep | awk | sort | uniq -c | sort -nr | head -1 一行命令定位日志中的“捣蛋鬼”IP。
Linux 底层验证：亲自操作了 chmod 750/644，验证了软链接（删源文件即失效）与硬链接（共用 inode 依然存活）的区别；制造并观察了僵尸进程（Z 状态），明白了 kill -9 杀不死它的原理。
代码正规军：将 D2 的找 IP 脚本重构为 d14_refactor 包，分离了 parser.py 与 main.py，并且成功跑通了 pytest 自动化测试。
1. D15 产出：
服务托管：编写了 d15-server.service，用 systemd 将 Python 服务注册为开机自启、崩溃自动拉起（Restart=always）的系统守护进程。
故障演练手册：在 d15_troubleshooting.md 中记录了亲手制造的 3 个故障（端口占用、权限拒绝、磁盘满）的“现象-排查-根因-修复”全过程。
API 服务：用 FastAPI 写好了 /health、/echo、/upload 三个接口，并直接通过 http://127.0.0.1:8001/docs 看到了 Swagger 交互文档。
接口自动化：使用 TestClient 编写了 3 个测试用例，跑出全绿的结果。
🧠 二、 知识图谱（核心认知升级）
1. 排查的“剥洋葱”思维：大厂面试问“502 怎么查”，不是在考背命令。真正的链路是：先用 curl -w 拆时间，分清是网络慢还是服务处理慢；再看 systemctl status 确认进程死活；接着用 journalctl -u 查报错日志；最后用 ss -lntp 确认端口监听。从外到内，用证据说话。
2. FastAPI 的核心模型：FastAPI 不只是写个 @app.get。它彻底搞定了数据校验：URL 里的参数用 Query（如 /echo?message=xxx），请求体里的文件用 Body（如 /upload），而在返回时可以用 response_model 过滤敏感字段。如果有参数校验失败，它连函数都不进，直接返回 422。
3. 自动化测试的边界：普通的函数测试用 assert，而 API 测试要用 TestClient。它在进程内直接模拟 ASGI 请求，不用真的启动服务，速度快且不依赖网络环境。
💣 三、 踩坑与排雷（最真实的工程日常）
这两天踩的坑，含金量极高，全被我写进了排障记录里：
1. systemd 找不到文件（status=2）：兴冲冲配好 d15-server.service，结果 systemctl status 一直是 activating (auto-restart) 且报错 status=2。破案：文件名是 d15_server.py，但服务配置里的路径写错了文件夹。修改 ExecStart 的绝对路径后满血复活。
2. 僵尸进程的“隐身术”：用 ps aux | grep "python3 -c" 死活找不到 Z 状态。原来子进程死后，名字会变成 [python3] <defunct>，原命令被系统抹掉了。要用 ps -ef | grep defunct 才能揪出它。
3. 磁盘满的“极限拉扯”：用 fallocate 挂载了一个 10M 的镜像，df -h 显示 100%。但用 echo 往里写文件却报 Permission denied。原来挂载点属于 root。用 sudo tee 提权后，居然还能写进去！原来 ext4 文件系统给 root 留了 5% 的“急救保留块”。最后用 dd if=/dev/zero 才彻底把空间塞满，逼出了 No space left on device。
4. FastAPI 启动闪退：代码写得没问题，但一运行 uvicorn 就报红。仔细看最后一行：RuntimeError: Form data requires "python-multipart"。原来处理文件上传需要额外安装依赖，pip install python-multipart 解决。
5. pytest 路径迷航：在 tests 目录下直接跑 pytest，报错 ModuleNotFoundError: No module named 'main'。原来 Python 解释器在当前的 tests 目录下找不到上一级的 main.py。退回到 d15_api 根目录再运行，或者在测试文件开头用 sys.path.insert 把上级目录加进去，问题迎刃而解。




D14 这一天的目的是把你 D1-D10 学过的零散知识，变成肌肉记忆。我们现在不讲“大厂追问”，也不讲“高深原理”，就实打实地在终端里敲代码，看结果。
请打开你的 WSL 终端（或者在 VS Code 里连接到 WSL），我们一步步来。你可以把下面的命令直接复制粘贴到终端里看效果。
任务 1：从日志里找“捣蛋鬼”IP（约 50 分钟）
目的：你 D2 写过 Python 脚本找 IP，现在我们要用 Linux 的命令，一行代码搞定。
第 1 步：准备一个“案发现场”
在终端里，进入你的项目目录，然后我们伪造一个 sample.log 文件：
bash
cd ~/Project_A_V3  # 确保你在项目目录下，如果你建在其他地方，请切换过去
cat << 'EOF' > sample.log
192.168.1.100 ERROR 数据库连接失败
10.0.0.55 INFO 用户登录成功
192.168.1.100 ERROR 接口超时
172.16.0.23 ERROR 磁盘空间不足
192.168.1.100 ERROR 密码错误
10.0.0.55 ERROR 验证码错误
EOF
解释：这行命令生成了一个包含几行报错日志的 sample.log 文件，里面 192.168.1.100 这个 IP 出现了 3 次 ERROR，是最多的。
第 2 步：像剥洋葱一样拆解命令
不要一上来就跑一长串命令，我们一块块看：
1. 先把包含 ERROR 的行拿出来：
bash
grep "ERROR" sample.log
（你应该能看到 4 行带 ERROR 的记录）
1. 把每一行的第 1 列（也就是 IP）切出来：
bash
grep "ERROR" sample.log | awk '{print $1}'
（你应该能看到 4 个 IP，其中 192.168.1.100 出现了 3 次）
1. 把相同的 IP 排在一起，并数一数有几个：
bash
grep "ERROR" sample.log | awk '{print $1}' | sort | uniq -c
（你会看到输出类似：3 192.168.1.100 和 1 10.0.0.55 等等。uniq -c 就是用来计数的）
1. 按数字从大到小排序，并只取第 1 名：
bash
grep "ERROR" sample.log | awk '{print $1}' | sort | uniq -c | sort -nr | head -1
（完美，输出的一定是 3 192.168.1.100。sort -nr 意思是按数值倒序排，head -1 意思是只看第一行）
你的验收动作：
1. 关掉我的回答，自己从头把上面那串长命令敲一遍。
2. 尝试修改一下，如果只想看日志最后两行的 ERROR，命令怎么打？（答案：把开头的 grep "ERROR" sample.log 改成 tail -2 sample.log | grep "ERROR"）。
任务 2：建文件夹、改权限、做链接（约 50 分钟）
目的：搞清楚 Linux 里最烦人的“数字权限”和“两个链接”。
第 1 步：建目录和文件
bash
mkdir -p d14_task/bin d14_task/conf d14_task/logs
touch d14_task/conf/app.conf
（这会在当前目录建一个 d14_task 文件夹，里面有三个子文件夹。conf 里有一个 app.conf 文件）
第 2 步：改权限（750 和 644）
bash
chmod 750 d14_task/bin
chmod 644 d14_task/conf/app.conf
然后你用 ls -l d14_task/ 看一下：
bash
ls -l d14_task/
预期结果：你会看到 bin 文件夹前面的权限是 drwxr-x---（这就是 750）；conf 文件夹里是 drwxr-xr-x（默认的 755），而 app.conf 是 -rw-r--r--（这就是 644）。
解释：750 里的 7（属主读写执行），5（属组读和执行），0（其他人啥也不能干）。为什么 bin 不给其他人权限？因为这是放脚本的地方，怕别人乱动。
第 3 步：搞事情！软链接 vs 硬链接
1. 先给 app.conf 做两个“分身”：
bash
cd d14_task/conf
ln -s app.conf app.conf.soft  # 软链接（相当于快捷方式）
ln app.conf app.conf.hard     # 硬链接（相当于同一个人的两个名字）
1. 看看它们长什么样：
bash
ls -l
（你会发现软链接前面有个箭头 app.conf.soft -> app.conf，而硬链接看起来和原文件一样）
1. 见证奇迹的时刻：我们把“本体”删除！
bash
rm app.conf
1. 分别打开这两个分身：
bash
cat app.conf.hard
（能正常打开，因为硬链接和本体共用同一个数据块。删了本体，数据还在）
bash
cat app.conf.soft
（报错！No such file or directory，因为软链接只是个指路牌，路牌指的文件被删了，路牌就废了）
任务 3：生与死——进程与僵尸（约 50 分钟）
目的：亲眼见一下 kill -9 杀不死的东西。
第 1 步：正常的杀死进程
在终端里敲：
bash
sleep 1000 &
（& 意思是让它在后台跑，它会返回一个数字，比如 [1] 1234，这个 1234 就是 PID）
现在找到它：
bash
ps aux | grep "sleep 1000"
找到 PID 那一列的数字，用 kill -9 杀掉它：
bash
kill -9 你的PID数字
第 2 步：制造一个“僵尸”
我们写一个只有 5 行的 Python 脚本，让它生个孩子然后不管它。
在终端里直接复制运行这段代码（它会放在后台）：
bash
python3 -c "
import os, time
pid = os.fork()
if pid == 0:
    exit()  # 子进程立刻死掉
else:
    time.sleep(300)  # 父进程睡大觉，不去收尸
" &
第 3 步：观察僵尸
现在立刻敲：
bash
ps aux | grep "python3 -c"
预期结果：你会看到两行 Python 进程。其中一行，它的 STAT（状态）列，写着一个大大的 Z，而且它对应的命令后面带有 <defunct> 字样。
这就是僵尸进程！它已经死了，但因为父进程没收尸，它一直挂在进程表里。
试一试：你能 kill -9 杀掉这个 Z 吗？
bash
kill -9 那个Z状态的PID
敲完之后，再用 ps aux | grep "python3 -c" 看一眼，它还在！
（正确的做法是杀掉它的“爸爸”，也就是上面那个 sleep(300) 的父进程，孩子就会被系统接管清理了）
傍晚（1.5 小时）：代码重构与录音
第 1 步：把 D2 的代码改造成“正规军”
不用搞得特别复杂。在终端建个新文件夹：
bash
mkdir -p d14_refactor/src d14_refactor/tests
touch d14_refactor/src/__init__.py
把你之前找 IP 的 Python 代码，拆成两部分：
在 src/parser.py 里写个函数：
python
# src/parser.py
def find_top_error_ip(file_path):
    # 写你 D2 学过的逻辑：打开文件，找出含 ERROR 的行，统计 IP，返回最多的
    pass
在 src/main.py 里调用它：
python
# src/main.py
import argparse
from parser import find_top_error_ip
﻿
# 用 argparse 接收用户传来的文件路径，打印结果
在 tests/test_parser.py 里用 pytest 测一下你这个函数对不对。
第 2 步：录音（2 分钟）
用手机录音或者微信语音发给自己。看着你自己刚才敲的终端，讲一段话：
“如果公司的 Nginx 突然报 502 错误，我的排障顺序是这样的：首先，我会用 systemctl status nginx 看看服务活着没；如果活着，我会去 /var/log/nginx/error.log 看报错；如果提示连不上后端，我会用 ss -tulnp 看后端的 Python 端口是不是挂了；最后我会用 df -h 看看是不是磁盘满了。总之，从外到内，一层层查。”
第 3 步：交作业
把代码推送到 Git：
bash
git add d14_task/ d14_refactor/ sample.log
git commit -m "D14: linux tasks done, refactor practice"



D15 上午的任务，就是把你 D9—D10 已经零散做过的 systemd、journalctl、ss、curl，串成这条“先分层、再深挖”的排查链路，并且主动制造 3 个故障，让“503/502/端口占用”从“别人的故事”变成你亲手处理过的证据。下午的 FastAPI，则是让你从“写脚本”跨到“写服务”——AI 应用交付岗的日常工作，大量时间是在写/调 API、写数据校验、写响应模型，而不是手撕算法。
二、上午（3h）：Linux 任务日 2——服务托管 + 网络排障 + 制造 3 个故障
任务 1（约 40 分钟）：用 systemd 托管一个 Python http.server
为什么要做：你 D9—D10 已经用过 systemctl is-active 查服务状态，但还没有亲手把一个 Python 进程注册成系统服务。大厂的 AI 应用交付/运维，服务不是用 python xxx.py & 跑的，而是由 systemd 托管、开机自启、崩溃自动拉起。Restart=always 是生产级的第一道防线——任何崩溃都会在 5 秒内自动恢复。﻿
操作步骤（在 WSL 里完成）：
1. 创建一个极简的 Python HTTP 服务文件 d15_server.py：
python
# d15_server.py
from http.server import HTTPServer, BaseHTTPRequestHandler
﻿
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK from D15 server\n")
﻿
if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
1. 创建 systemd unit 文件：
bash
sudo tee /etc/systemd/system/d15-server.service > /dev/null << 'EOF'
[Unit]
Description=D15 Python HTTP Server
After=network.target
﻿
[Service]
Type=simple
User=shenk
WorkingDirectory=/home/shenk/Project_A_V3
ExecStart=/usr/bin/python3 /home/shenk/Project_A_V3/d15_server.py
Restart=always
RestartSec=5
﻿
[Install]
WantedBy=multi-user.target
EOF
1. 重载 systemd 并启动：
bash
sudo systemctl daemon-reload
sudo systemctl start d15-server
sudo systemctl enable d15-server   # 开机自启
1. 验证：
bash
systemctl status d15-server
curl -s http://127.0.0.1:8080
你应该看到 active (running)，并且 curl 返回 OK from D15 server。
验收标准：关掉教程后，你能从空文件写出 unit 文件，并解释 Restart=always 和 RestartSec=5 的作用（崩溃后 5 秒自动拉起）。
大厂追问：“如果服务反复重启，systemctl status 里能看到什么？”（能看到最近几次退出码和重启次数，指向崩溃原因。）
任务 2（约 40 分钟）：journalctl + ss + curl 三层排查
为什么要做：大厂面试问“502 怎么排查”，要的不是“背命令”，而是能说出先看哪一层、用什么证据排除。这一步是把 D14 的“单条命令”串成“排查链路”。
操作步骤：
1. journalctl 查服务日志：
bash
journalctl -u d15-server -n 50 --no-pager
journalctl -u d15-server --since "5 min ago" -p err
解释：-u 指定服务，-n 50 看最近 50 行，-p err 只看 error 级别。﻿
1. ss 查端口监听：
bash
ss -lntp | grep :8080
解释：-l 只显示监听，-n 数字端口，-t TCP，-p 显示进程。你应看到 0.0.0.0:8080 和 python3 的 PID。﻿
1. curl 分层计时：
bash
curl -o /dev/null -s -w "dns:%{time_namelookup} conn:%{time_connect} total:%{time_total}\n" http://127.0.0.1:8080/
解释：time_connect 高说明建连慢（网络/服务端忙），time_total 远高于 time_connect 说明服务端处理慢。
验收标准：你能口述：“如果 curl 的 time_connect 正常但 time_total 很大，我会先去 journalctl 看服务日志，而不是先 ping。”
任务 3（约 60 分钟）：主动制造 3 个故障，并写排查记录
为什么要做：D14 你已经制造过僵尸进程，D15 要制造的是交付/运维岗真正会遇到的 3 类故障：端口占用、权限拒绝、磁盘满。只有亲手制造过，面试时才能讲出“我遇到的是什么现象、我先看了什么、根因是什么”。
故障 1：端口占用
1. 先停掉 d15-server：
bash
sudo systemctl stop d15-server
1. 用一个临时进程占住 8080：
bash
python3 -m http.server 8080 &
1. 再启动 d15-server，观察 systemctl status 或 journalctl -u d15-server -n 20 里的报错。预期现象：Address already in use。﻿排查记录写法：现象 → ss -lntp | grep :8080 看到被另一个 python3 占用 → 先 kill 占用进程，再 systemctl start d15-server。
故障 2：权限拒绝
1. 把 d15_server.py 的权限改成不可读：
bash
chmod 000 d15_server.py
sudo systemctl restart d15-server
journalctl -u d15-server -n 20 --no-pager
预期现象：Permission denied。﻿
排查记录写法：现象 → journalctl 看到 Permission denied → ls -l d15_server.py 发现权限是 ---------- → chmod 644 恢复。﻿﻿
故障 3：磁盘满模拟
1. 创建一个小的 loop 设备并挂载到临时目录（WSL 下可用 fallocate + mkfs + mount，或者更简单地用一个已满的分区/目录模拟）：
bash
mkdir -p /tmp/d15_full
fallocate -l 10M /tmp/d15_full.img
mkfs.ext4 /tmp/d15_full.img
sudo mount -o loop /tmp/d15_full.img /tmp/d15_full
df -h /tmp/d15_full   # 看到 100% used
1. 尝试向 /tmp/d15_full 写文件：
bash
echo "test" > /tmp/d15_full/test.txt
预期现象：No space left on device。
排查记录写法：现象 → df -h 看到挂载点 100% → 清理或扩容 → 再次写入成功。完成后 sudo umount /tmp/d15_full。
验收标准：三个故障都有“现象 → 排查命令 → 根因 → 修复”四段式记录，放进 d15_troubleshooting.md。
大厂追问：“502 是不是一定意味着进程挂了？”（不一定。systemctl status 可能仍是 active (running)，502 可能来自 Nginx 到后端的连接失败、超时、worker 饱和等。）
上午的 Git 提交
bash
git add d15_server.py d15_troubleshooting.md
git commit -m "D15: systemd service + 3 fault injections (port/permission/disk) + troubleshooting log"
三、下午（4h）：FastAPI 入门——3 个接口 + 3 个 pytest
任务 4（约 90 分钟）：写 /health、/echo、/upload 三个接口
为什么要做：AI 应用交付岗的日常，大量时间在写/调 API 和数据校验。FastAPI 的核心不是“会写 @app.get”，而是理解 Query / Body / Response Model 各自管什么：Query 管 URL 参数，Body 管请求体，response_model 管“只输出该输出的字段”。Pydantic 在 FastAPI 中负责数据校验，如果客户端少传了字段，FastAPI 会在进入函数前直接截断请求，返回 422 错误。﻿
操作步骤：
在你的 d15_http 目录（或者新建一个 d15_api 目录），确认你的虚拟环境 (venv) 激活状态，敲：
bash
pip install fastapi uvicorn httpx pytest
pip install python-multipart

1. 新建 d15_api/ 目录，创建 main.py：
python
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
﻿
app = FastAPI()
﻿
# 1. /health — 无参数，返回固定状态
@app.get("/health")
def health():
    return {"status": "ok"}
﻿
# 2. /echo — Query 参数
@app.get("/echo")
def echo(message: str = "hello"):
    return {"echo": message}
﻿
# 3. /upload — Body（文件上传）
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    return {"filename": file.filename, "size": len(content)}
1. 启动：
bash
cd d15_api
uvicorn main:app --reload --host 0.0.0.0 --port 8001

打开你终端右上角的 + 号开一个新终端，输入以下命令，看看是不是都通了：
1. 测健康检查：
bash
curl http://127.0.0.1:8001/health
（预期：{"status":"ok"}）
2. 测 Query 参数：
bash
curl "http://127.0.0.1:8001/echo?message=hello_d15"
（预期：{"echo":"hello_d15"}）
3. 测文件上传：
先造一个测试文件，再传上去：
bash
echo "hello this is D15" > test.txt
curl -F "file=@test.txt" http://127.0.0.1:8001/upload
（预期：返回文件名和它的大小）
验收标准：
* /health 返回 {"status":"ok"}。
* /echo?message=xxx 返回 {"echo":"xxx"}，不传 message 时返回默认值。
* /upload 能收到文件并返回文件名和大小。
* 打开 http://127.0.0.1:8001/docs，能看到自动生成的 Swagger 文档。
关于 Query / Body / Response Model 的追问：
* Query：/echo?message=xxx 里的 message 是 Query 参数，FastAPI 自动从 URL 解析并做类型校验。
* Body：/upload 的文件是 Body；如果写 JSON 接口，用 Pydantic BaseModel 定义 Body，FastAPI 会自动校验并返回 422 错误。
* Response Model：用 response_model 可以过滤敏感字段（比如密码不返回）并保证输出结构一致。D15 先不强制加 response_model，但要知道它是“控制输出”的工具。

任务 5：写 3 个自动化测试（约 20 分钟）
虽然 curl 跑通了，但大厂交付更看重“自动化测试”。我们在 d15_api 目录下建一个 tests 文件夹，并写测试用例。
第一步：在 d15_api 下新建 tests 文件夹。
第二步：在 tests 里新建 test_main.py，把这段代码复制进去：
python
from fastapi.testclient import TestClient
from main import app
﻿
client = TestClient(app)
﻿
def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
﻿
def test_echo_default():
    response = client.get("/echo")
    assert response.status_code == 200
    assert response.json() == {"echo": "hello"}
﻿
def test_upload():
    response = client.post(
        "/upload",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["size"] == 11
第三步：在终端运行（确保你装了 pytest 和 httpx）：
bash
pip install pytest httpx
python -m pytest tests/ -v
只要看到绿色的 3 passed，你的接口测试就大功告成了！
下午的 Git 提交
bash
git add d15_api/
git commit -m "D15: FastAPI 3 endpoints + pytest TestClient"
