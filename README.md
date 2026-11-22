# AI Companion

一个用于学习大模型后端开发的陪伴型 AI 聊天服务。目标不是做模型训练，而是把 **上下文工程、提示词工程、工具调用/MCP、SSE 流式输出** 这条链路亲手实现一遍。

> 当前状态：P3 第一阶段已实现（手写 AgentLoop、本地时间工具、MCP stdio 时间 Server、Open-Meteo 真实天气、`tool_calls` 审计；39 tests passed；PG 迁移 `0003_tool_calls` 已应用）。

## 学习目标

- 上下文工程：token 预算、滑动窗口、滚动摘要、长期记忆、RAG
- 提示词工程：角色卡分层、版本化、评测
- 工具调用与 MCP：本地 stdio、远程 Streamable HTTP、权限与审计
- 流式输出：SSE 事件协议、心跳、取消、断线重连
- 工程化：幂等、限流、重试/降级、观测、测试

## 非目标

- 模型训练、微调、推理引擎优化
- 一开始就做多模态、语音、复杂多智能体
- 直接改 MsgRail（C++ IM）；Phase 2 才通过接口集成

## 文档

- [交接文档：从这个项目怎么开始](docs/00-handoff.md)
- [架构设计](docs/01-architecture.md)
- [技术方案：API、SSE、表结构、测试](docs/02-tech-design.md)
- [Phase 2 与 MsgRail 的集成契约](docs/03-integration-contract.md)

## 快速开始

### 1. 启动 PostgreSQL

**方式 A：apt 安装（推荐，避免 Docker Hub 拉取问题）**

```bash
sudo apt update
sudo apt install -y postgresql
sudo service postgresql start
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'ai_companion';"
sudo -u postgres createdb ai_companion
```

如果提示数据库已存在，忽略即可。`pg_isready` 应返回 `accepting connections`。

**方式 B：Docker**

```bash
sudo docker run -d --name ai-pg \
  -e POSTGRES_PASSWORD=ai_companion \
  -e POSTGRES_DB=ai_companion \
  -p 5432:5432 \
  -v ai-pg-data:/var/lib/postgresql/data \
  pgvector/pgvector:pg16
```

如果希望免 sudo：`sudo usermod -aG docker $USER && newgrp docker`。

> P1 不需要 pgvector 扩展；P4 做长期记忆时再安装。Docker Hub 拉取超时时，直接用方式 A。

### 2. 安装依赖并迁移

```bash
cd ~/Linux/AI_Companion
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.asgi:app --reload --port 8000
```

如果 `python3 -m venv` 提示缺少 ensurepip，先执行：

```bash
sudo apt update && sudo apt install -y python3-venv
```

如果 editable install 的构建依赖拉取失败，可以绕过它直接装：

```bash
pip install fastapi "uvicorn[standard]" pydantic-settings httpx openai python-dotenv \
  "sqlalchemy[asyncio]" asyncpg alembic pytest pytest-asyncio respx ruff aiosqlite \
  -i https://pypi.tuna.tsinghua.edu.cn/simple
```

打开 <http://localhost:8000>。默认 `LLM_PROVIDER=fake`，不需要 API Key。

接真实模型（DeepSeek 示例），编辑 `.env`：

```dotenv
LLM_PROVIDER=openai_compat
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=deepseek-chat
```

用 curl 验证 SSE：

```bash
curl -N -X POST http://localhost:8000/v1/chat/stream \
  -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -d '{"message":"你好"}'
```

跑测试（使用 SQLite 内存库，不需要 PostgreSQL）：

```bash
PYTHONPATH=. python -m pytest -q
```

P1 新增接口：

- `GET /v1/conversations`：会话列表
- `GET /v1/conversations/{id}/messages`：历史消息
- `POST /v1/conversations`：新建会话
- `DELETE /v1/conversations/{id}`：归档会话

`POST /v1/chat/stream` 现在会自动创建/续用 `conversation_id`，并把历史一起发给模型。

## P2：上下文预算与滚动摘要

默认配置：

```dotenv
CONTEXT_WINDOW_TOKENS=32768
SUMMARY_ENABLED=true
SUMMARY_TRIGGER_RATIO=0.7
SUMMARY_KEEP_RECENT_MESSAGES=6
SUMMARY_MAX_TOKENS=512
SUMMARY_MODEL=qwen-turbo
SUMMARY_TEMPERATURE=0.2
SUMMARY_SYNC=false
TOKEN_SAFETY_MARGIN=1.15
```

- 上下文按 token 预算装配，不再按消息条数硬截断。
- 历史被裁剪，或未摘要 token 超过“可用历史预算”的 70% 时，触发滚动摘要。
- 摘要由 `qwen-turbo` 生成，存 `summaries` 表，下一轮自动注入 system prompt。
- 默认后台异步生成；测试可设 `SUMMARY_SYNC=true`。

想快速看到摘要效果，可以临时把窗口调小：

```dotenv
CONTEXT_WINDOW_TOKENS=1000
LLM_MAX_TOKENS=200
SUMMARY_TRIGGER_RATIO=0.2
SUMMARY_KEEP_RECENT_MESSAGES=2
SUMMARY_SYNC=true
```

重启后聊 3~4 轮，然后查库：

```bash
sudo -u postgres psql -d ai_companion \
  -c "SELECT conversation_id, up_to_message_id, left(content, 80), token_count FROM summaries ORDER BY id DESC LIMIT 3;"
```

验证完记得把窗口参数恢复成默认值。

## P3：工具调用与 MCP

P3 第一阶段包含：

- 手写 AgentLoop：模型 → `tool_call` → 执行 → `tool_result` → 再调模型；
- 统一 `ToolRegistry`：本地工具 + MCP 工具；
- 本地时间工具 + MCP stdio 时间 Server；
- MCP stdio 天气 Server（数据来源：Open-Meteo 真实数据）；
- `tool_calls` 审计表；
- 只读工具自动执行，写/危险工具不暴露；
- 工具超时、结果截断、最大步数、并行上限。

安装 MCP SDK：

```bash
source .venv/bin/activate
python -m pip install "mcp>=1.0,<2" -i https://pypi.tuna.tsinghua.edu.cn/simple
```

重启 uvicorn 后，MCP Server 会在 lifespan 中启动。测试：

> 现在几点？

预期 SSE 中出现 `tool_call`、`tool_result`，最终回答包含当前时间。工具调用会写入：

```bash
sudo -u postgres psql -d ai_companion \
  -c "SELECT run_id, tool_name, server_name, status, latency_ms FROM tool_calls ORDER BY id DESC LIMIT 5;"
```

Streamable HTTP 是第二阶段，尚未实现。

