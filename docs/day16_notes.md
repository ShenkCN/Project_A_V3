# 🚀 D16 总结：SQL 索引优化与 Docker 容器化全链路交付
## 🎯 一、 今日战果（产出清单）﻿
1. **RAG 项目数据库底座**：编写了 `schema.sql`，建好了 `documents`、`chunks`、`tickets` 三张表，并理清了它们之间的外键约束与联合索引。
2. **SQL 执行计划分析**：通过 `EXPLAIN` 验证了最左前缀原则，亲眼对比了全表扫描（`type=ALL`）与走索引（`type=ref`）、覆盖索引（`Using index`）的巨大差异。
3. **生产级 Dockerfile**：将 D15 的 FastAPI 服务打包成镜像，使用了多阶段构建（减小体积）、非 root 用户（提升安全）、并配置了 `HEALTHCHECK`。
4. **容器编排**：编写 `docker-compose.yml`，把 FastAPI 和 MySQL 串联起来，实现了数据卷持久化和依赖健康检查。﻿
---
## 🧠 二、 知识图谱（核心认知升级）
### 1. SQL 优化：不是背命令，是看“证据”
- **三表设计的考量**：`chunks` 表用 `(document_id, chunk_index)` 做联合索引，是因为 RAG 检索最常做的动作就是“按文档 ID 过滤，按顺序取块”。
- **最左前缀原则**：`WHERE chunk_index = 0` 绝对走不了索引，因为跳过了最左边的 `document_id`，B+ 树的无序性导致无法检索。
- **覆盖索引**：如果 `SELECT` 的列刚好全在联合索引里，`Extra` 列会显示 `Using index`，直接免去了“回表”查主键的操作，性能极高。
### 2. Docker：容器化不是“打包”，是“环境隔离与编排”
- **多阶段构建**：`builder` 阶段装依赖，`runtime` 阶段只拷贝装好的依赖。镜像里不带编译工具链，不仅小，而且攻击面小。
- **非 root 用户**：在 Dockerfile 里用 `USER appuser`。万一容器被攻破，攻击者拿到的只是普通用户权限，无法直接控制宿主机。
- **编排的健康检查**：`depends_on` 只能保证容器**启动**，不保证服务**就绪**。必须配合 `condition: service_healthy` 和 `mysqladmin ping`，让 API 等 MySQL 彻底准备好再启动。
--
## 💣 三、 踩坑与排雷（最真实的工程日常）
今天可以说是“排雷大作战”，把 Docker 踩了个底朝天：
1. **权限被拒（Permission Denied）**：
   - **现象**：敲 `docker build` 时报错 `permission denied while trying to connect to the docker API`。
   - **排查**：虽然执行了 `usermod -aG docker`，但当前终端未刷新用户组。
   - **解决**：当前终端直接无脑加 `sudo`，或者彻底退出重开终端。
2. **拉取基础镜像超时（I/O Timeout）**：
   - **现象**：`FROM python:3.10-slim` 卡住报错，拉取不下来。
   - **解决**：配置国内 Docker 镜像加速器（如 1ms.run, 轩辕镜像等），修改 `/etc/docker/daemon.json` 并重启 Docker。
3. **找不到文件（requirements.txt）**：
   - **现象**：Docker build 报错 `COPY failed: file not found`。
   - **根因**：要在 `d15_api` 目录下构建，但虚拟环境在上一级。需要先激活 venv，用 `pip freeze > requirements.txt` 导出依赖，再返回构建。
4. **Compose 插件缺失**：
   - **现象**：`docker compose up` 报错 `unknown command` 或 `apt install docker-compose-plugin` 找不到包。
   - **解决**：通过 `curl` 直接下载官方二进制文件到 `/usr/local/lib/docker/cli-plugins/docker-compose` 并赋予执行权限。
5. **配置语法废弃警告**：
   - **现象**：启动 Compose 报黄字 `attribute 'version' is obsolete`。
   - **解决**：新版 Compose 已经不需要写版本号，删掉 yml 文件第一行的 `version: "3.9"`。
---
## 💡 四、 大厂面试问答准备（费曼输出）
**Q1：如果 API 启动时 MySQL 还没 ready，你的应用代码应该怎么处理？**
> **满分回答**：首先在编排层面，我会用 `depends_on` 配合 `condition: service_healthy`，等 MySQL 探针通了再启动 API。其次在代码层面，我会配置连接重试机制（比如 `pool_pre_ping`），如果重试失败，就让容器退出（Exit），利用 Compose 的重启策略自动拉起，绝不让半死不活的容器对外提供服务。
**Q2：为什么 Dockerfile 里要把 `COPY requirements.txt .` 放在 `COPY . .` 之前？**
> **满分回答**：利用 Docker 的层缓存机制。如果没有新的依赖变更，每次只改动业务代码时，Docker 不会重新执行 `pip install`，构建速度会从几分钟秒降到几秒钟。
**Q3：`EXPLAIN` 里的 `type=ALL` 和 `Using index` 分别意味着什么？**
> **满分回答**：`type=ALL` 说明发生了全表扫描，性能极差，通常是因为没有索引或违反了最左前缀。`Using index` 说明触发了覆盖索引，查询所需的所有列都在索引树上，不需要回表查主键，这是最理想的状态。


Docker 方面，AI 应用交付岗要求能写出非 root、多阶段构建、带健康检查的生产级 Dockerfile，而不是 FROM python:3.9 一把梭。docker compose 要能把 FastAPI 和 MySQL 编排在一起，并且理解 depends_on 不保证 MySQL 已就绪、需要用 condition: service_healthy 配合 mysqladmin ping。Volume 持久化是必考：容器删了数据不能丢。
二、上午（3h）：SQL 速通——建库建表 + CRUD + JOIN + EXPLAIN
任务 1（约 40 分钟）：建 knowledge_base 库和三张表
为什么要做：RAG 项目的“文档 → 切分块 → 工单”天然对应三张表。面试官问“你 RAG 项目的数据库怎么设计的”，你需要能画出 documents、chunks、tickets 的表结构和关系，而不是只说“用了 Chroma”。
在 WSL 里确保 MySQL 已安装并启动（sudo service mysql start），然后登录：
bash
sudo mysql -u root -p
创建库和表（这就是 D19 RAG 项目的数据库骨架）：
sql
CREATE DATABASE IF NOT EXISTS knowledge_base DEFAULT CHARSET utf8mb4;
USE knowledge_base;

CREATE TABLE documents (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL COMMENT 'pdf/docx/markdown',
    file_path VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE chunks (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    document_id BIGINT UNSIGNED NOT NULL,
    chunk_index INT UNSIGNED NOT NULL,
    content TEXT NOT NULL,
    token_count INT UNSIGNED DEFAULT 0,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_doc_chunk (document_id, chunk_index),
    CONSTRAINT fk_chunks_doc FOREIGN KEY (document_id) REFERENCES documents(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tickets (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status TINYINT UNSIGNED DEFAULT 0 COMMENT '0=open,1=in_progress,2=resolved',
    priority TINYINT UNSIGNED DEFAULT 1 COMMENT '1=low,2=medium,3=high',
    related_chunk_id BIGINT UNSIGNED,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_status_priority (status, priority),
    KEY idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
验收标准：SHOW TABLES; 能看到三张表；DESC chunks; 能看到 idx_doc_chunk 联合索引；能口述“chunks 为什么用 (document_id, chunk_index) 做联合索引”（RAG 检索时经常按文档过滤、按顺序取块）。
大厂追问：“tickets 的 status 和 priority 为什么用 TINYINT 而不是 VARCHAR？”（枚举值用无符号整数，存储小、比较快、可加注释表达语义。）
任务 2（约 50 分钟）：CRUD + JOIN + 20 条常用查询
为什么要做：交付岗的日常不是写“炫技 SQL”，而是写能被同事看懂、能加索引、不会拖垮数据库的查询。D16 至少覆盖 INSERT、SELECT、UPDATE、DELETE、JOIN、GROUP BY、ORDER BY、LIMIT。
插入测试数据：
sql
INSERT INTO documents (title, source_type, file_path) VALUES
('运维SOP-打印机故障', 'markdown', '/docs/printer.md'),
('门店网络排障手册', 'pdf', '/docs/network.pdf'),
('工单处理规范', 'docx', '/docs/ticket.docx');

INSERT INTO chunks (document_id, chunk_index, content, token_count) VALUES
(1, 0, '打印机卡纸时先断电，再打开后盖取出纸张。', 20),
(1, 1, '如果反复卡纸，检查搓纸轮是否磨损。', 18),
(2, 0, '门店网络不通时，先 ping 网关，再检查交换机端口。', 25);

INSERT INTO tickets (title, description, status, priority) VALUES
('打印机卡纸', '3号机反复卡纸', 0, 2),
('门店断网', '收银台无法联网', 0, 3),
('账号锁定', '员工账号被锁', 2, 1);
写 20 条常用 SQL（以下为示例，要求你自己手敲并执行）：
sql
-- 1. 查询所有 open 状态的工单
SELECT * FROM tickets WHERE status = 0;

-- 2. 按优先级降序查询 open 工单
SELECT * FROM tickets WHERE status = 0 ORDER BY priority DESC;

-- 3. 查询每个文档的 chunk 数量
SELECT d.title, COUNT(c.id) AS chunk_count
FROM documents d
LEFT JOIN chunks c ON d.id = c.document_id
GROUP BY d.id, d.title;

-- 4. 查询某个文档的第 0 个 chunk
SELECT * FROM chunks WHERE document_id = 1 AND chunk_index = 0;

-- 5. 查询最近创建的 3 张工单
SELECT * FROM tickets ORDER BY created_at DESC LIMIT 3;

-- 6. 更新某张工单的状态
UPDATE tickets SET status = 1 WHERE id = 1;

-- 7. 删除某个文档及其 chunks（先删 chunks 再删 document，或依赖外键级联）
DELETE FROM chunks WHERE document_id = 3;
DELETE FROM documents WHERE id = 3;

-- 8. 统计各状态工单数量
SELECT status, COUNT(*) AS cnt FROM tickets GROUP BY status;

-- 9. 查询标题包含“打印机”的工单
SELECT * FROM tickets WHERE title LIKE '%打印机%';

-- 10. 查询有 chunk 的文档（INNER JOIN）
SELECT DISTINCT d.id, d.title
FROM documents d
INNER JOIN chunks c ON d.id = c.document_id;
验收标准：20 条 SQL 都能执行；能解释 LEFT JOIN 和 INNER JOIN 在这组数据上的结果差异；能说出“为什么删除 documents 之前要先处理 chunks”（外键约束）。
任务 3（约 60 分钟）：EXPLAIN——亲眼看到“索引失效”和“索引生效”
为什么要做：面试官不会问“索引是什么”，会问“这条 SQL 为什么没走索引”。D16 要让你亲手制造一次 type=ALL 的全表扫描，再用索引把它变成 type=ref。
步骤 1：先看“没有索引”的查询计划
sql
-- chunks 表目前只有 (document_id, chunk_index) 联合索引
EXPLAIN SELECT * FROM chunks WHERE content LIKE '%打印机%';
观察 type 列：大概率是 ALL（全表扫描）。Extra 里可能出现 Using where。
步骤 2：制造“索引生效”的查询计划
sql
EXPLAIN SELECT * FROM chunks WHERE document_id = 1 AND chunk_index = 0;
观察 type 列：应该是 ref 或 range，key 列显示 idx_doc_chunk。这证明最左前缀 document_id 被用上了，chunk_index 也被用上了。
步骤 3：验证“最左前缀截断”
sql
-- 只给 chunk_index，不给 document_id：联合索引失效
EXPLAIN SELECT * FROM chunks WHERE chunk_index = 0;
预期 type=ALL，key=NULL。这就是最左前缀原则：跳过最左列，后面的列在 B+ 树里是无序的，无法用索引。
步骤 4：验证“覆盖索引避免回表”
sql
-- 查询列全部包含在联合索引中
EXPLAIN SELECT document_id, chunk_index FROM chunks WHERE document_id = 1;
观察 Extra 列：应该出现 Using index（覆盖索引），而不是 Using index condition（需要回表）。这是面试高频得分点。
验收标准：截图保存 type=ALL 和 type=ref 两次 EXPLAIN 的对比；能口述“为什么 WHERE chunk_index = 0 不走索引，而 WHERE document_id = 1 走索引”。
大厂追问：“LIKE '%打印机%' 能走索引吗？LIKE '打印机%' 呢？”（前者不能，后者能，因为前缀通配符破坏了最左前缀的有序性。）
上午的 Git 提交
bash
git add d16_sql/
git commit -m "D16: knowledge_base schema + CRUD/JOIN queries + EXPLAIN index comparison"
三、下午（4h）：Docker 速通——Dockerfile + Docker Compose
任务 4（约 90 分钟）：写一个生产级 FastAPI Dockerfile
为什么要做：D15 的 FastAPI 服务是在宿主机上跑的，交付岗要的是镜像。面试官会看你的 Dockerfile 有没有多阶段构建、有没有非 root 用户、有没有 .dockerignore。
在 d15_api/ 目录下创建 Dockerfile：
dockerfile
# syntax=docker/dockerfile:1
FROM python:3.10-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.10-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN useradd -r -m appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
创建 .dockerignore：
text
venv/
__pycache__/
.pytest_cache/
*.pyc
.env
关键点解释（面试时能讲出来）：
* 多阶段构建：builder 阶段装依赖，最终镜像只拷贝 /install，不带编译工具，镜像更小。
* 非 root 用户：USER appuser，容器逃逸时攻击面更小。
* HEALTHCHECK：让编排系统知道服务是否真的活着，而不是进程在但 /health 不通。
* 依赖层缓存：COPY requirements.txt 在 COPY . . 之前，依赖不变时构建秒完成。
验收：
bash
cd d15_api
（先安装docker）
sudo apt update
sudo apt install docker.io -y
sudo service docker start
sudo usermod -aG docker $USER
exit退出终端重新开
还需要把venv的requirements.txt依赖导出
pip freeze > requirements.txt
# 1. 构建镜像
sudo docker build -t d15-api:v1 .
# 2. 运行容器
sudo docker run -d -p 8000:8000 --name d15-api-test d15-api:v1
# 3. 测试健康检查
curl http://127.0.0.1:8000/health
# 4. 看看容器是不是真的跑起来了
sudo docker ps

sudo docker logs d15-api-test
sudo docker stop d15-api-test && docker rm d15-api-test
大厂追问：“COPY . . 为什么要放在 COPY requirements.txt 之后？”（利用 Docker 层缓存，代码变动不会导致依赖重新安装。）
任务 5（约 90 分钟）：docker compose 拉起 FastAPI + MySQL
为什么要做：交付岗不会只交付一个容器。RAG 项目至少需要 app + mysql 两个服务，docker compose 是一键拉起和后续部署到云服务器的基础。
创建 docker-compose.yml（放在 d15_api/ 同级或项目根目录）：
yaml
version: "3.9"

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: knowledge_base
      MYSQL_USER: shenk
      MYSQL_PASSWORD: shenkpass
    ports:
      - "3307:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./d16_sql/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uroot", "-prootpass"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    build: ./d15_api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: mysql+pymysql://shenk:shenkpass@mysql:3306/knowledge_base
    depends_on:
      mysql:
        condition: service_healthy

volumes:
  mysql_data:
关键点解释：
* condition: service_healthy ：depends_on 默认只保证 MySQL 容器启动，不保证能接受连接。加上健康检查条件后，api 会等 MySQL 真正 ready 再启动。
* Volume 持久化：mysql_data 挂在 /var/lib/mysql，删掉容器数据还在。
* 初始化 SQL：./d16_sql/schema.sql 挂到 /docker-entrypoint-initdb.d/，MySQL 首次启动会自动执行建表。
启动与验证：
bash
（先安装 Docker Compose 插件）
# 1. 创建 Docker CLI 插件目录
sudo mkdir -p /usr/local/lib/docker/cli-plugins
# 2. 下载 Compose V2 稳定版二进制文件
sudo curl -fsSL "https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose
# 3. 赋予执行权限
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
# 4. 验证是否安装成功
docker compose version

docker compose ps          # 应该看到 mysql 是 Up (healthy)，api 是 Up
docker compose logs api    # 确认 Uvicorn running
curl http://127.0.0.1:8000/health
进入 MySQL 容器验证表已创建：
bash
docker compose exec mysql mysql -ushenk -pshenkpass knowledge_base -e "SHOW TABLES;"
验收标准：docker compose ps 两个服务都是 Up 且 MySQL 是 healthy；SHOW TABLES 能看到 documents、chunks、tickets；能口述“depends_on 和 condition: service_healthy 的区别”。
大厂追问：“如果 api 启动时 MySQL 还没 ready，你的应用代码应该怎么处理？”（连接重试或让容器退出并由 compose 重启，同时 readiness 检查应该失败。）
下午的 Git 提交
bash
git add d15_api/Dockerfile d15_api/.dockerignore docker-compose.yml
git commit -m "D16: production Dockerfile (multi-stage, non-root, healthcheck) + compose with MySQL"
