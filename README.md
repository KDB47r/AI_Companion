# AI Companion

一个用于学习大模型后端开发的陪伴型 AI 聊天服务。目标不是做模型训练，而是把 **上下文工程、提示词工程、工具调用/MCP、SSE 流式输出** 这条链路亲手实现一遍。

> 当前状态：P0 已实现并验证（9 个测试通过；uvicorn 实机 curl 验证 SSE 事件序列）。多轮与持久化在 P1。

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

```bash
cd ~/Linux/AI_Companion
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

如果 `python3 -m venv` 提示缺少 ensurepip，先执行：

```bash
sudo apt update && sudo apt install -y python3-venv
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

跑测试：

```bash
pytest -q
```

