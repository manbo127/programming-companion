# 程序设计学习智能学伴 "小码"

基于大语言模型的 Web 对话式编程学习助手，面向初学者的耐心陪伴者。

## 快速开始

### 1. 环境准备

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 和 FLASK_SECRET_KEY
```

### 3. 数据库初始化

```bash
flask db upgrade
python scripts/migrate_json_to_sqlite.py --dry-run  # 预览
python scripts/migrate_json_to_sqlite.py              # 迁移旧 JSON
```

### 4. 启动

```bash
python run.py
# 访问 http://127.0.0.1:5000
```

## 生产部署

阿里云 ECS 的 Nginx、Gunicorn、Systemd、HTTPS 与 SQLite 备份步骤见
[deploy/README.md](deploy/README.md)。生产环境请从 `.env.production.example`
创建 `.env`，不要直接复用开发配置。

## 测试

```bash
# 运行所有测试（无需网络）
python -m pytest tests/ -v

# 覆盖率
python -m pytest tests/ --cov=companion --cov-report=term
```

## 评测

```bash
# FakeLLM（无需网络）
python scripts/run_evaluation.py

# DeepSeek 实机（需配置 API Key）
python scripts/run_evaluation.py --live
```

## 项目结构

```
companion/          # 应用包
  api/              # REST API (8 Blueprint)
  models/           # SQLAlchemy 数据模型 (6表)
  repositories/     # 数据访问层
  services/         # 业务逻辑（ChatService, 分类, 激励）
  llm/              # LLM Gateway (DeepSeek + FakeLLM)
  prompts/          # 提示词模板 + 构建器
  utils/            # 代码工具（语言检测, 错误解析）
static/             # 前端 (8个JS模块)
templates/          # HTML 模板
tests/              # pytest 测试 (32用例)
scripts/            # 迁移 + 评测脚本
docs/               # 详细文档
```

## 技术栈

- Python 3 + Flask 3.x
- SQLite + SQLAlchemy 2.x + Alembic
- DeepSeek API (OpenAI 兼容)
- 原生 HTML/CSS/JavaScript

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | API 密钥 | (必填) |
| `FLASK_SECRET_KEY` | Flask 密钥 | (生产必填) |
| `DATABASE_URL` | 数据库地址 | `sqlite:///instance/companion.db` |
| `APP_ENV` | 环境 | `development` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
