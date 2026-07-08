# 程序设计学习智能学伴后端

本目录是课程设计项目的后端部分，采用 Flask 实现，负责：

- 提供 `/api/chat` 聊天接口；
- 根据用户输入识别场景；
- 组织不同场景下的 Prompt；
- 调用 DeepSeek API；
- 使用 JSON 文件保存聊天记录。

## 目录结构

```text
backend/
├── app.py                  # Flask 入口文件，定义后端接口
├── config.py               # 配置文件，读取环境变量
├── llm_client.py           # DeepSeek API 调用封装
├── prompt_builder.py       # Prompt 模板与上下文拼接
├── intent_classifier.py    # 基于规则的意图识别
├── memory_manager.py       # 聊天记录 JSON 读写
├── data/
│   └── chat_history.json   # 聊天历史记录
└── requirements.txt        # Python 依赖
```

## 启动方式

先安装依赖：

```bash
pip install -r requirements.txt
```

设置 DeepSeek API Key：

```bash
set DEEPSEEK_API_KEY=你的APIKey
```

启动后端：

```bash
python app.py
```

默认地址：

```text
http://127.0.0.1:5000
```

## 主要接口

### 1. 健康检查

```http
GET /api/health
```

### 2. 智能学伴聊天

```http
POST /api/chat
Content-Type: application/json
```

请求示例：

```json
{
  "message": "这个代码为什么报错？",
  "code": "print(a)",
  "error": "NameError: name 'a' is not defined"
}
```

返回示例：

```json
{
  "success": true,
  "scene": "code_error",
  "reply": "这个错误说明变量 a 在使用前还没有定义……"
}
```

### 3. 获取历史记录

```http
GET /api/history
```

### 4. 清空历史记录

```http
POST /api/clear
```

## 场景分类

当前支持 4 类场景：

- `general_chat`：普通编程问答；
- `code_error`：代码错误解读；
- `problem_guidance`：解题思路引导；
- `encouragement`：学习鼓励反馈。

如果前端不传 `scene`，后端会根据关键词自动判断。
