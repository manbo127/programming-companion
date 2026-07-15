# 小码：程序设计学习智能学伴

“小码”是面向编程初学者的 Web 学习伙伴。它不直接替用户完成作业，而是结合代码、完整报错、对话上下文和学习画像，帮助用户定位原因、理解知识点并逐步形成自己的解题思路。

线上地址：[https://xiaomacode.xyz](https://xiaomacode.xyz)

## 已实现能力

- 四类对话场景：报错解读、解题引导、知识问答、自由交流
- Python、Java、C、C++、JavaScript、TypeScript、Go、Rust、SQL 识别与错误解析
- 结构化错误诊断，以及四阶段渐进式解题脚手架
- 上下文 Token 预算、较早对话摘要和跨对话安全画像
- 本地可审计知识库及 Python、Java、JavaScript、C++、Go、Rust、SQL 官方资料引用
- 学习主题、语言、错误、活跃天数、掌握度和趋势分析
- 1/3/7/14/30 天间隔复习计划与主动提醒
- 情绪标签、强度分数和温暖/平衡/简洁三种反馈风格
- 匿名直接使用；可选注册、登录、退出、跨设备同步和失败锁定
- DeepSeek V4 Flash、超时预算、分类重试、调用遥测和安全错误响应
- SQLite 默认持久化，Alembic 迁移；可切换 PostgreSQL
- Nginx + Gunicorn + Systemd + HTTPS 生产部署
- JSON 日志、健康/就绪/指标端点、数据库备份、冒烟检查和 CI

## 本地运行

要求 Python 3.11+。Node.js 仅用于检查前端 JavaScript 语法，不是运行依赖。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，至少填写：

```dotenv
DEEPSEEK_API_KEY=sk-你的密钥
FLASK_SECRET_KEY=一段随机长字符串
```

初始化并启动：

```powershell
python -m flask --app run:app db upgrade
python run.py
```

浏览器访问 [http://127.0.0.1:5000](http://127.0.0.1:5000)。开发环境未配置 DeepSeek Key 时使用 FakeLLM；生产环境缺少 Key 会拒绝启动模型请求，避免把测试回复误当成真实回答。

## 测试与检查

```powershell
python -m pytest -q
Get-ChildItem static/js/*.js | ForEach-Object { node --check $_.FullName }
python -m compileall -q companion scripts
python -m flask --app run:app db heads
```

部署后执行只读冒烟检查：

```bash
python scripts/smoke_test.py https://xiaomacode.xyz
```

运行时端点：

- `/api/v1/health`：存活和数据库连通性
- `/api/v1/ready`：核心表与模型配置就绪性
- `/api/v1/metrics`：不含用户文本、Cookie、密钥和数据库路径的聚合指标

## 数据库

默认数据库为 SQLite，位置由 `DATABASE_URL` 决定。升级代码后必须先执行迁移：

```bash
flask --app run:app db upgrade
```

一致性备份：

```bash
flask --app run:app backup-database --output-dir backups
```

切换 PostgreSQL 时，只需安装依赖并更换环境变量；应用会自动选择适合服务端数据库的连接池设置：

```dotenv
DATABASE_URL=postgresql://codemate:password@127.0.0.1:5432/codemate
```

## 生产部署

当前真实生产架构是阿里云香港 ECS 上的单机部署：

```text
Browser → HTTPS/Nginx → Gunicorn(gthread) → Flask
                                           ├─ SQLite
                                           └─ DeepSeek API
```

完整步骤见 [deploy/README.md](deploy/README.md)。仓库不再保留旧 Vercel 入口：Vercel Python Function 的临时文件系统不适合长期保存本项目的 SQLite 数据，且当前真实部署也不经过 Vercel。

## 项目结构

```text
companion/
  api/             REST API 与身份边界
  knowledge/       可审计知识条目与确定性检索
  llm/             DeepSeek/FakeLLM 网关
  models/          8 个 SQLAlchemy 模型（含可撤销账号会话）
  prompts/         人设、场景、知识和教学脚手架
  repositories/    数据访问层
  services/        对话、画像、分析、提醒和诊断业务
  utils/           语言检测与错误解析
migrations/        线性 Alembic 数据库迁移
static/            原生 CSS/JavaScript 前端
templates/         Jinja 页面
deploy/            Nginx 与 Systemd 配置
scripts/           迁移、评测、备份和冒烟检查
tests/             单元、集成与生产安全回归测试
```

## 关键环境变量

| 变量 | 作用 | 默认值 |
|---|---|---|
| `APP_ENV` | `development` / `production` | `development` |
| `FLASK_SECRET_KEY` | Cookie 与 CSRF 签名，生产必填 | 无安全默认值 |
| `DATABASE_URL` | SQLite 或 PostgreSQL 连接 | `instance/companion.db` |
| `DEEPSEEK_API_KEY` | DeepSeek 密钥 | 空 |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-v4-flash` |
| `DEEPSEEK_THINKING` | `enabled` / `disabled` | `disabled` |
| `DEEPSEEK_MAX_RETRIES` | 最大调用尝试次数 | `2` |
| `DEEPSEEK_TOTAL_TIMEOUT` | 整个模型调用时间预算 | `40` 秒 |
| `TRUST_PROXY_HOPS` | 可信反向代理跳数 | `0` |
| `CLIENT_COOKIE_SECURE` | 身份 Cookie 仅 HTTPS | 生产为 `true` |

真实密钥只放在 `.env` 或服务器密钥系统中，不提交到 Git。
