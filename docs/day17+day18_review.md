1. Linux 数字权限计算
Linux 文件权限分三类对象：属主 u、属组 g、其他人 o。
权限对应数字：r=4，w=2，x=1。三位数字分别表示 u、g、o 的权限和。
* 7 = 4+2+1 = rwx
* 5 = 4+1 = r-x
* 0 = ---
所以 750：
* 属主：7 = rwx，可读可写可执行
* 属组：5 = r-x，可读可进入/执行，不可写
* 其他人：0 = ---，无权限
注意：对文件来说 x 是执行权限；对目录来说 x 表示能否进入/遍历目录，r 表示能否列出目录内容，w 表示能否在目录中创建/删除文件。
2. 硬链接与软链接的本质区别
硬链接：多个文件名指向同一个 inode。inode 里维护链接计数，删除其中一个文件名只是减少计数，只有计数为 0 且无进程打开时数据才真正删除。所以删除原文件后，硬链接仍可用。硬链接一般不能跨文件系统，普通用户不能给目录建硬链接。
软链接：类似快捷方式，本身是一个独立文件，里面存的是目标路径。删除原文件后，软链接仍存在但变成“断链”，访问会失败。软链接可以跨文件系统，也可以指向目录。
一句话：硬链接共用 inode，软链接存路径。
3. 僵尸进程 Z 状态
子进程结束后，内核还保留它的退出状态等信息，等待父进程调用 wait()/waitpid() 回收。如果父进程一直不回收，子进程就变成僵尸进程，状态为 Z。
关键点：
* 僵尸进程已经死了，不再占用 CPU/内存主体，但占用进程表项。
* kill -9 对僵尸进程无效，因为它已经不能接收信号。
* 处理方式：让父进程回收；若父进程不处理，可杀死父进程，让 init/systemd 收养并回收子进程。
4. 不可中断睡眠 D 状态
D 状态表示进程正在等待底层 I/O，且处于不可中断睡眠。常见于磁盘 I/O、NFS 挂载异常等场景。
特点：
* 此时进程不响应信号，连 kill -9 也会被忽略/挂起。
* 不能简单靠杀进程解决，需要等 I/O 完成、修复存储/NFS，严重时只能重启。
* D 状态进程过多通常说明底层 I/O 或存储有问题。
5. systemd 自动拉起服务配置
服务单元文件通常放 /etc/systemd/system/xxx.service。常用配置：
ini
[Service]
Restart=always
RestartSec=5
* Restart=always：服务退出后自动重启。通常 systemctl stop 主动停止时不再拉起。
* RestartSec=5：重启前等待 5 秒，避免疯狂重启。
* 修改后执行 systemctl daemon-reload 再 systemctl restart xxx。
补充：on-failure 只在异常退出时重启；always 更激进。
6. systemctl enable 与 start 的区别
* systemctl enable xxx：设置开机自启，本质是创建启动依赖的符号链接，不立即启动。
* systemctl start xxx：立刻启动服务，但不会设置开机自启。
* systemctl enable --now xxx：既设置开机自启，又立刻启动。
* systemctl disable 取消开机自启，stop 停止当前服务。
7. journalctl 查日志
journalctl 查 systemd 日志。常用：
bash
journalctl -u nginx
journalctl -u nginx -p err
journalctl -u nginx --since "10 min ago"
* -u：指定服务单元名。
* -p：按日志级别过滤，如 err 只看错误及以上。
* --since：指定起始时间，也可配合 --until。
* -f：持续跟踪日志。
日志级别从高到低：emerg、alert、crit、err、warning、notice、info、debug。
8. ss -lntp 查端口
bash
ss -lntp
* -l：只看监听状态
* -n：端口显示数字，不做服务名解析
* -t：TCP
* -p：显示占用端口的进程 PID/程序名
用于排查“端口是否被监听、被哪个进程占用”。普通用户可能看不到其他用户进程 PID，需要 sudo。
9. ps 查资源占用
bash
ps aux --sort=-%CPU | head
* ps aux：显示所有进程详细信息。
* --sort=-%CPU：按 CPU 使用率倒序，- 表示降序。
* head：取前几行。
类似可查内存：ps aux --sort=-%MEM | head。生产排查时还要结合 top、htop、pidstat。
10. curl 耗时拆解
bash
curl -o /dev/null -s -w "DNS:%{time_namelookup} TCP:%{time_connect} TLS:%{time_appconnect} TTFB:%{time_starttransfer} Total:%{time_total}\n" URL
* -o /dev/null：丢弃响应体
* -s：静默模式
* -w：按格式输出耗时
各阶段：
* time_namelookup：DNS 解析耗时
* time_connect：TCP 建连耗时
* time_appconnect：TLS 握手耗时
* time_starttransfer：首字节时间，包含服务端处理
* time_total：总耗时
用于判断慢在 DNS、网络、TLS 还是服务端处理。
11. FastAPI 的 422 错误
FastAPI 使用 Pydantic 做请求参数校验。当客户端：
* 缺少必填字段
* 字段类型不对
* 枚举/约束不满足
Pydantic 校验失败时，FastAPI 直接返回 422 Unprocessable Entity，不会进入路由函数体。响应里通常有 detail 说明哪个字段出错。这也是 FastAPI 的优势：参数校验前置、自动生成文档。
12. FastAPI 文件上传依赖
处理 File(...)、UploadFile 时需要安装：
bash
pip install python-multipart
否则运行时会报错，提示需要 python-multipart。因为文件上传使用 multipart/form-data，FastAPI/Starlette 需要该库解析表单。
13. FastAPI 参数类型
* Path 参数：URL 路径中的参数，如 /users/{user_id}，函数参数用 user_id: int。
* Query 参数：URL ? 后面的参数，如 /items?q=abc&limit=10，函数中普通参数默认就是 Query。
* Body 参数：请求体，通常是 Pydantic 模型，如 item: Item。
* 也可用 Path(...)、Query(...)、Body(...) 显式声明校验和元数据。
14. FastAPI 不内置 ORM
FastAPI 只负责路由、依赖注入、参数校验、OpenAPI 文档等，不内置数据库 ORM。实际项目常配合：
* SQLAlchemy
* SQLModel
* Tortoise ORM
* 数据库驱动如 asyncpg、pymysql
所以“FastAPI 做 Web 层，ORM 做数据层”是常见架构。
15. FastAPI 装饰器指定方法
python
@app.post("/items")
def create_item():
    ...
@app.post 表示该路由只接收 POST 请求。用 GET 访问会返回 405 Method Not Allowed。类似还有 @app.get、@app.put、@app.delete、@app.patch。
16. TestClient 作用
fastapi.testclient.TestClient 用于 pytest 中模拟请求，在内存中调用 ASGI 应用，不需要真正启动 Uvicorn 服务器。
示例：
python
from fastapi.testclient import TestClient
client = TestClient(app)
resp = client.get("/")
适合写接口测试、校验状态码和响应体。注意它模拟的是应用层请求，不是完整生产网络环境。
17. Docker 镜像与容器关系
* 镜像：只读模板，类似面向对象里的“类”。由多层文件系统组成。
* 容器：镜像的运行实例，类似“对象/实例”。在镜像只读层之上加一个可写层。
一个镜像可以启动多个容器；容器删除后，未持久化的可写层数据会丢失。
18. Dockerfile 多阶段构建
多阶段构建示例：
dockerfile
FROM python:3.11 AS builder
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt
﻿
FROM python:3.11-slim
COPY --from=builder /install /usr/local
COPY . .
作用：编译/安装依赖阶段和最终运行阶段分开，最终镜像只拷贝产物，不包含编译工具和缓存，体积更小、攻击面更小、更安全。
19. Dockerfile 中 CMD 与 ENTRYPOINT
* CMD：默认命令。docker run image 新命令 会覆盖 CMD。
* ENTRYPOINT：入口命令，通常不会被 docker run 后面的参数覆盖，后面的参数会作为 entrypoint 的参数追加。可用 --entrypoint 显式覆盖。
常见组合：ENTRYPOINT ["python"] + CMD ["app.py"]，运行时传其他脚本即可替换默认参数。
20. Dockerfile 中的 USER
USER 指定容器运行时使用的用户。默认容器内是 root，风险较大。使用非 root：
dockerfile
RUN useradd -m appuser
USER appuser
好处：容器逃逸或应用被攻破时，攻击者权限较低，降低对宿主机威胁。注意切换用户前要保证应用文件有相应读/写/执行权限。
21. Dockerfile 中的 EXPOSE
EXPOSE 8000 只是文档声明/元数据，告诉使用者容器内应用监听哪个端口，不会真正把端口发布到宿主机。真正映射要在 docker run 时用 -p，或在 compose 中写 ports。
22. Docker 端口映射
bash
docker run -p 8080:80 nginx
格式：-p 宿主机端口:容器端口。访问宿主机 8080 会转发到容器 80。还有 -p 127.0.0.1:8080:80 只绑定本机回环地址，更安全。
23. Docker 层缓存原理
Dockerfile 每条指令通常生成一层。只要某层及其之前层未变化，就能复用缓存。
推荐：
dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
先把依赖文件单独 COPY 并安装，再 COPY 源码。这样源码改动不会导致依赖安装层缓存失效，构建更快。
24. Docker Volume 数据卷
Volume 用于持久化数据。容器删除后，volume 中的数据仍保留在宿主机 Docker 管理目录中。
示例：
bash
docker run -v mysql_data:/var/lib/mysql mysql
MySQL 数据目录 /var/lib/mysql 必须持久化，否则删容器数据丢失。还有 bind mount：-v /host/path:/container/path。
25. docker compose up -d
docker compose up -d 启动 compose 中定义的服务，-d 表示 detached，即后台运行。不加 -d 会前台占用终端并输出日志。常用 docker compose up -d --build 重新构建镜像后启动。
26. docker compose logs 与 exec
* docker compose logs：查看服务日志，-f 持续跟踪，docker compose logs -f web 看指定服务。
* docker compose exec web bash：进入正在运行的容器内部执行命令，类似 docker exec -it。
exec 要求容器正在运行；run 则是新建一个一次性容器执行命令。
27. docker compose 健康检查依赖
depends_on 默认只保证启动顺序：先启动依赖容器，再启动当前容器，但不保证依赖容器“完全就绪”。
要等依赖健康后再启动，需要：
yaml
depends_on:
  db:
    condition: service_healthy
同时 db 服务要配置 healthcheck。否则应用可能先启动，连数据库失败。生产中还常配合应用重试机制。
28. MySQL 联合索引最左前缀原则
联合索引 (a,b,c) 使用时必须从最左列开始连续匹配：
* where a=? 可用
* where a=? and b=? 可用
* where a=? and b=? and c=? 可用
* where b=? 或 where c=? 通常不能用该索引
* where a=? and c=? 只能用到 a
范围查询后，后续列可能无法继续用于精确索引查找。设计索引要按查询条件顺序考虑。
29. EXPLAIN 的 type 列
EXPLAIN 看执行计划，type 表示访问类型，常见从差到好大致：
* ALL：全表扫描，最差
* index：全索引扫描
* range：范围扫描，使用索引
* ref：非唯一索引等值匹配
* eq_ref：唯一索引/主键关联匹配
* const：常量查找，很快
type=ALL 通常要关注是否缺索引或条件无法走索引。
30. EXPLAIN 的 Extra 列
Extra 提供额外信息：
* Using index：覆盖索引，查询列都在索引中，无需回表，很好。
* Using where：使用 where 过滤。
* Using filesort：需要额外文件排序，较差，常见于 order by 无合适索引。
* Using temporary：使用临时表，常见于 group by/order by，较差。
出现 filesort/temporary 要结合业务看是否可优化索引。
31. SQL 索引失效场景
常见索引失效：
1. LIKE '%abc%'：左边带通配符，无法从索引左前缀定位。
2. 对索引列使用函数：如 where date(create_time)=...，可改为范围查询。
3. 隐式类型转换：字符串列用数字比较，或数字列用字符串比较。
4. OR 两侧部分列无索引。
5. 不符合最左前缀。
6. 不等于、否定条件有时导致优化器放弃索引。
是否走索引最终由优化器根据成本决定，要用 EXPLAIN 验证。
32. SQL LEFT JOIN
LEFT JOIN 以左表为主：左表每行都保留，右表有匹配则拼接右表字段，无匹配则右表字段为 NULL。
常用于“查左表所有记录，并附带右表信息”。如果 where 中对右表字段加非空条件，可能把 LEFT JOIN 效果变成 INNER JOIN，需要放到 ON 或注意条件位置。
33. WHERE 与 HAVING
* WHERE：在 GROUP BY 之前过滤行，不能直接用聚合函数。
* HAVING：在 GROUP BY 之后过滤分组，可使用聚合函数。
示例：
sql
SELECT dept, COUNT(*) 
FROM emp 
WHERE status=1 
GROUP BY dept 
HAVING COUNT(*) > 10;
先 WHERE 过滤行，再分组，再 HAVING 过滤组。
34. SQL TINYINT
TINYINT 占 1 字节：
* 有符号：-128 到 127
* 无符号 UNSIGNED：0 到 255
适合存状态码，如 0=待处理、1=完成、2=失败。状态值少时比 INT 省空间，但可读性不如枚举/注释，设计时要有文档或字典表。
35. 日志词频统计经典命令
bash
grep "ERROR" app.log | awk '{print $1}' | sort | uniq -c | sort -nr | head
流程：
* grep：过滤目标日志行
* awk '{print $1}'：取第一列，比如 IP 或时间
* sort：排序，让相同内容相邻
* uniq -c：统计连续重复次数
* sort -nr：按次数倒序数字排序
* head：取前几名
用于快速找高频 IP、高频错误、高频 URL 等。
36. grep -v 参数
grep -v 表示反向匹配，输出不包含指定关键字的行。
示例：
bash
grep -v "DEBUG" app.log
常用于排除噪音日志。可配合 -i 忽略大小写，-E 使用扩展正则。
37. pytest 找不到主模块
在 tests/ 目录下运行 pytest 时，Python 的模块搜索路径可能不包含上级目录，导致找不到上级 main.py。
临时解决：
python
import sys
sys.path.insert(0, '..')
更规范的做法：
* 在项目根目录运行 pytest
* 使用 conftest.py 调整路径
* 把项目做成可安装包，pip install -e .
* 配置 pyproject.toml/pytest.ini 的 pythonpath
sys.path.insert(0, '..') 是快速办法，但生产测试建议用规范包结构。
38. Python 依赖导出
在虚拟环境激活状态下：
bash
pip freeze > requirements.txt
会把当前环境已安装包及版本导出。安装：
bash
pip install -r requirements.txt
注意 pip freeze 会包含间接依赖。若想只导出直接依赖，可用 pipreqs 或维护 pyproject.toml/requirements.in + pip-compile。
总体复习口诀
* 权限：rwx=421，三位属组其他人
* 链接：硬链共 inode，软链存路径
* 进程：Z 等父回收，D 等 I/O 不能杀
* systemd：enable 开机，start 现在；Restart 拉起
* 排查：journalctl 日志，ss 端口，ps 资源，curl 耗时
* FastAPI：422 校验失败，File 要 multipart，Path/Query/Body 分清
* Docker：镜像是类，容器是实例；多阶段瘦身，Volume 持久化
* MySQL：最左前缀，EXPLAIN 看 type/Extra，WHERE 行 HAVING 组
* 命令：grep 过滤，awk 取列，sort/uniq 统计
* Python：路径问题 sys.path，依赖导出 pip freeze


一、 单选题考点解析（30题）
【Linux 权限与进程（底层机制）】
1. umask 掩码：umask 就像一块“遮光板”。如果系统默认新建文件全给 666（读写），新建目录全给 777（读写执行）。umask 是 022，意思是把属组和其他人的写权限（2）给遮掉。你算算 666 减去 022 剩多少？
2. SGID（目录强制位）：你看到权限里有一个 s 在属组（Group）位置。它在目录上的作用是：只要有人在这个目录里创建新文件，新文件的属组会强制继承这个目录的属组，而不是创建者自己的主组。常用于团队共享目录。
3. killall 与 pkill：kill 只能杀指定 PID；killall 是杀指定进程名的所有实例；pkill 更高级，可以用正则模糊匹配进程名。-15 是礼貌劝退，-9 是当场击毙。
4. top 排序：在 top 界面里，按大写的 P 是按 CPU 排序，按大写的 M 是按内存排序，按 T 是按运行时间。
5. ss -s：ss 命令不仅能查端口（-lntp），加 -s（summary）可以看整个系统的网络连接统计，比如有多少个 TIME_WAIT 状态的连接，这对于排查服务器卡顿极其有用。
6. 数字权限的陷阱：chmod 777 是直接覆盖成读写执行；chmod +x 是追加执行权限。如果你原本是 600（读写），执行 777 就变成啥都能干；执行 +x 就变成 700。
【systemd 服务与日志】
1. After 和 Requires：After 只管时间顺序（我排在你后面启动），不管依赖死活。Requires 是硬依赖（你死了我也活不成）。生产环境通常这两个配着用。
2. journalctl --since today：查当天的日志，--since 是关键参数，后面跟时间词（today, yesterday, "1 hour ago"）。
3. failed (Result: exit-code)：看到这个，说明服务启动后自己崩溃退出了（比如代码抛出异常、找不到配置文件）。你要去查具体的 journalctl 日志找抛出异常的代码行。
【FastAPI 进阶】
1. Optional 可选字段：在 Pydantic 模型里，如果你不给字段写默认值（如 name: str），前端传过来少了这个字段就会直接报错 422。如果你写 name: str = None 或者用 Optional，它就变成选填了。
2. 参数强类型校验：前端传了字符串 "true"，而你后端定义的是 bool 类型。Pydantic 极其严格，不会自作聪明帮你转，直接拦截返回 422 报错。
3. 接口分类：在 @app.get(..., tags=["用户管理"]) 中加 tags，你的 Swagger 文档就会把这些接口分门别类，看起来很专业。
【Docker 核心机制】
1. ADD 和 COPY：COPY 是最傻白甜的复制，只负责把本地文件塞进镜像。ADD 是个多面手：如果遇到压缩包，它会自动解压；如果遇到 URL，它会自动下载。但官方推荐，除非需要解压或下载，否则只用 COPY。
2. --rm 参数：通常用于一次性任务（比如跑个测试脚本）。跑完退出后，容器自动销毁，不留垃圾。
3. Compose 网络：你在哪个文件夹下运行 docker compose up，它就会自动建一个 文件夹名_default 的专属网络，让你的容器在这个隔离的网络里互相通信。
4. WORKDIR 的作用：它就像 cd 命令，且后面所有的 RUN、COPY 等指令，都在这个目录下执行。如果你在 /app 下 touch test.txt，文件就在 /app 里。
【SQL 进阶】
1. possible_keys 与 key：你可能建了 3 个索引，但优化器选了其中一个。possible_keys 是备胎（可能用到的），key 是正宫（实际生效的）。
2. 最左前缀原则：联合索引 (name, age)，相当于按 name 排序，name 相同再按 age 排。如果你直接查 age，那它是乱序的，查不了。必须带上最左边的 name。
3. VARCHAR 与 CHAR：CHAR(50) 雷打不动占 50 个字符（即使你只存了 1 个，它也补空格）。VARCHAR(50) 存 1 个就只占 1 个的空间加长度记录。但 CHAR 处理速度极快。适合存固定长度的（如身份证、手机号）。
4. TRUNCATE 与 DELETE：DELETE 是逐行删，可以回滚（undo log），且不重置自增主键。TRUNCATE 是直接摧毁数据页，速度快，不可回滚，且自增 ID 归零。
5. %abc% 全表扫描：这是经典的性能杀手。B+树是查前缀的，你搞个左边是通配符，数据库直接懵了，只能把 100 万行数据逐行拿出来对比。
6. Volume 痛点：Volume 是由 Docker 管理的，你如果想在宿主机上直接打开文件看，很麻烦（还得进去找）。Bind Mount 才是你随便在宿主机改的。
【综合排坑】
1. pip freeze 污染：如果你在全局环境执行，会把系统里所有的乱七八糟包全导出来，别人一安装直接依赖冲突报错。
2. port is already allocated：老熟人。你映射的宿主机端口（如 8000）已经被别的进程（比如你之前没关的 Uvicorn）占了。
3. Connection refused 排除法：如果你明明敲了 curl 命令，但报这个错。说明网络底层根本没通。绝不可能是因为“代码里的 JSON 结构不对”（因为请求根本没到代码层）。
4. docker logs -f：同 tail -f，实时看日志。
5. mv 覆盖：Linux 里 mv 如果目标文件已存在，默认动作是“覆盖（重命名）”。
6. curl -v：打印详细的连接过程，包括客户端请求了啥、服务器返回了啥 Header，是排障利器。
7. compose down：默认只删除容器和网络，保留你的数据卷。如果你想连数据一起删，得加 -v。
8. FastAPI 的 def 与 async def：FastAPI 极其聪明。你写普通 def，它会把它丢到线程池里去跑，不会卡死主线程；只有写 async def 且里面用了 await 才是真异步。
二、 多选题考点解析（20题）
1. 硬链接的规矩：只能在同一个硬盘分区（文件系统）里建；不能给目录建（防止死循环）；它和源文件是同一个 inode，所以内容同步。
2. 僵尸进程 Z：父进程不管孩子（没 wait），孩子就变成僵尸。父进程如果死了，僵尸进程会被系统（init/systemd）接管清理。
3. Restart=always 与 on-failure：on-failure 只有程序崩溃（非0退出）才重启。always 是只要没在运行就拉起来。但如果你手动执行 systemctl stop，它不会再次拉起，因为系统尊重你的手动操作。
4. journalctl 参数：-u 是服务，-p 是级别，--since 是时间，-f 是追踪。
5. Docker 网络模式：bridge（默认）、host（直接占用宿主机端口，不用-p）、none（无网络）、overlay（集群模式）。
6. depends_on 的局限：它只管容器启动，不保证里面的服务就绪（比如 MySQL 启动要好几秒才能连）。必须配合 healthcheck。
7. Dockerfile 指令：COPY/ADD 管文件，WORKDIR 切目录，RUN 执行命令。
8. 最左前缀：只要包含了最左边的 a，并且没有断档（a=1 and b>2 能用到a和b的索引，但后面的c因为b是范围查询而断裂），就能用上索引。
9. EXPLAIN 的 type：const（主键或唯一索引）、ref（非唯一索引）、range（范围索引）、ALL（全表扫，不算索引）。
10. LEFT JOIN 的退化：如果左连接了，但在 WHERE 里面要求右表字段不能为 NULL，那左表没匹配的行就被干掉了，效果完全等同于 INNER JOIN。
11. pytest 断言：写代码的等号是 == 判断，不是 = 赋值。
12. Pydantic：类型不对会抛异常，但 FastAPI 会接住这个异常，优雅地返回 422 JSON 给前端，不会让程序崩溃。
13. 4xx 状态码：400 参数错，401 没登录，403 没权限，404 找不到。
14. 磁盘满排查：df（看大盘）、du（看小文件夹）、find（找大文件）。
15. Volume 安全：Volume 独立于容器生命周期，删容器不删数据。
16. 重定向与管道：< 和 > 是重定向，| 是管道。把 ls 结果当字符串给 grep 处理。
17. ENTRYPOINT 覆盖：如果基础镜像用了 ENTRYPOINT（比如 uvicorn main:app），你在 docker run 后面追加参数，会被当成 uvicorn 的参数，而不是替换 uvicorn。
18. TestClient：它直接和你的 FastAPI 应用通信，不经过网络层，极快。
19. slim 镜像：官方精简版，去掉了多余的编译工具（gcc等），体积小，安全。
20. 容器资源监控：docker stats 像任务管理器；docker top 像 Linux 的 ps，看进程。
三、 填空题考点解析（20题）
1. SIGCONT：SIGSTOP 是暂停，SIGCONT 是继续（Continue）。
2. 运行（Running）：R 就是 Running，S 是 Sleep，D 是等 I/O，Z 是僵尸。
3. /dev：dev 是 device（设备）的缩写。鼠标、键盘、硬盘全在这。
4. enable：使能、开启。
5. Priority：优先级。
6. OpenAPI：FastAPI 底层就是基于 OpenAPI 规范生成文档的。
7. 200：OK，成功。
8. int：数据类型声明。
9. ENV：Environment 的缩写。写进 Dockerfile 里，构建和运行时都能用。
10. 当前目录：去当前目录找 Dockerfile。
11. 数据卷（Volume）：down -v 就是连本地数据卷一起扬了。
12. AVG()：平均值。
13. ASC：Ascending（升序），DESC 是降序。
14. 聚簇（Clustered）：InnoDB 的主键就是数据本身，数据和主键索引长在一起，叫聚簇索引。
15. temporary（Using temporary）：临时表。
16. 参数：CMD 里的内容会作为参数，追加给 ENTRYPOINT 里的命令。
17. --tail：尾巴，最后几行。
18. 事件循环（Event Loop）：异步编程的心脏，被阻塞了，整个服务就卡住了。
19. chgrp：change group。
20. test_：这是 pytest 认测试用例的招牌。

