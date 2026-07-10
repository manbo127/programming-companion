# 阿里云 ECS 生产部署

本方案面向单台 Ubuntu 24.04 ECS：Nginx 对外提供 HTTPS，Gunicorn 仅监听
`127.0.0.1:8000`，应用使用本机 SQLite。由于 SQLite 和当前会话内状态的特点，
Gunicorn 固定为 **1 个 worker + 4 个线程**。

以下命令假定：

- 项目目录：`/srv/codemate`
- 服务账户：`codemate`
- 域名：`code.example.com`（需要替换）
- Systemd 服务：`codemate.service`

## 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y git nginx sqlite3 python3 python3-venv python3-pip
sudo adduser --disabled-password --gecos "" codemate
sudo mkdir -p /srv/codemate /var/backups/codemate
sudo chown -R codemate:codemate /srv/codemate /var/backups/codemate
```

## 2. 上传代码并安装 Python 依赖

推荐使用只读 Deploy Key 从 Git 仓库拉取：

```bash
sudo -u codemate git clone YOUR_REPOSITORY_URL /srv/codemate
cd /srv/codemate
sudo -u codemate python3 -m venv .venv
sudo -u codemate .venv/bin/pip install --upgrade pip
sudo -u codemate .venv/bin/pip install -r requirements.txt
```

## 3. 创建生产配置

```bash
openssl rand -hex 32
sudo -u codemate cp .env.production.example .env
sudo -u codemate nano .env
sudo chmod 600 .env
```

至少替换 `FLASK_SECRET_KEY` 和 `DEEPSEEK_API_KEY`。保持：

```dotenv
APP_ENV=production
TRUST_PROXY_HOPS=1
SESSION_COOKIE_SECURE=true
CLIENT_COOKIE_SECURE=true
DATABASE_URL=sqlite:////srv/codemate/instance/companion.db
```

不要把 `.env` 上传到 Git，也不要把 API Key 写进 Systemd 或 Nginx 配置。

## 4. 初始化数据库

```bash
sudo -u codemate mkdir -p /srv/codemate/instance
sudo -u codemate bash -c '
  cd /srv/codemate
  set -a
  source .env
  set +a
  .venv/bin/flask --app run:app db upgrade
'
```

## 5. 安装 Systemd 服务

```bash
sudo cp deploy/systemd/codemate.service /etc/systemd/system/codemate.service
sudo systemctl daemon-reload
sudo systemctl enable --now codemate
sudo systemctl status codemate --no-pager
curl --fail http://127.0.0.1:8000/api/v1/health
```

实时查看日志：

```bash
sudo journalctl -u codemate -f
```

## 6. 安装 Nginx 配置

先将 `deploy/nginx/codemate.conf` 中的 `code.example.com` 替换为真实域名，然后：

```bash
sudo cp deploy/nginx/codemate.conf /etc/nginx/sites-available/codemate
sudo ln -s /etc/nginx/sites-available/codemate /etc/nginx/sites-enabled/codemate
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

ECS 安全组只公开 `80/443`；`22` 只允许管理员 IP；不要开放 `5000/8000`。

## 7. 开启 HTTPS

域名 A 记录指向 ECS 公网 IP 且解析生效后：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d code.example.com --redirect
sudo certbot renew --dry-run
```

生产配置使用 Secure Cookie，因此完整业务验收必须通过 HTTPS 域名进行。

## 8. 配置 SQLite 每日备份

```bash
sudo chmod +x /srv/codemate/scripts/backup_sqlite.sh
sudo -u codemate /srv/codemate/scripts/backup_sqlite.sh
sudo crontab -u codemate -e
```

加入：

```cron
20 3 * * * /srv/codemate/scripts/backup_sqlite.sh >> /var/backups/codemate/backup.log 2>&1
```

脚本默认保留 14 天，使用 SQLite 在线备份命令，不会遗漏 WAL 中已经提交的数据。

## 9. 更新版本

先备份数据库，再拉取、迁移并重启：

```bash
sudo -u codemate /srv/codemate/scripts/backup_sqlite.sh
sudo -u codemate git -C /srv/codemate pull --ff-only
sudo -u codemate /srv/codemate/.venv/bin/pip install \
  -r /srv/codemate/requirements.txt
sudo -u codemate bash -c '
  cd /srv/codemate
  set -a
  source .env
  set +a
  .venv/bin/flask --app run:app db upgrade
'
sudo systemctl restart codemate
curl --fail https://code.example.com/api/v1/health
```

## 10. 故障排查

```bash
sudo systemctl status codemate --no-pager
sudo journalctl -u codemate -n 200 --no-pager
sudo nginx -t
sudo tail -n 200 /var/log/nginx/error.log
curl -v http://127.0.0.1:8000/api/v1/health
curl -v https://code.example.com/api/v1/health
```

如果未来需要多台 ECS 或多个 Gunicorn worker，应先将 SQLite 迁移到 PostgreSQL、
MySQL 或阿里云 RDS，并将进程内状态迁移到共享存储。
