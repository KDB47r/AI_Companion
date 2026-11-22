# 00 · 交接文档

> 这份文档用于跨会话/跨工作目录交接。新会话先读这里，再读 `01-architecture.md` 和 `02-tech-design.md`。

## 1. 背景

用户在做两个学习项目：

1. `Spark_Push` / MsgRail：C++17 分布式 IM，用于学习长连接、消息路由、Kafka 异步解耦、可靠投递。
2. `AI_Companion`（本项目）：类似抖音“小火人”的 AI 陪伴聊天机器人，用于学习 Agent 工程能力。

本项目**不碰模型底层**：不做训练/微调，直接调用厂商 API（DeepSeek/Qwen/GLM）或后续接本地开源模型（Ollama/vLLM）都可以。

## 2. 目标与非目标

### 目标

- 上下文工程：token 预算、滑动窗口、滚动摘要、长期记忆、RAG
- 提示词工程：角色卡、分层 system prompt、版本化、评测
- 工具调用与 MCP：本地 stdio server、远程 Streamable HTTP、权限与审计
- SSE 流式输出：事件协议、心跳、取消、断线重连
- 工程化：幂等、限流、重试/降级、观测、测试

### 非目标

- 模型训练、微调、推理优化
- 一开始就做多模态/语音/复杂多智能体
- 直接改 MsgRail 的 C++ 代码

## 3. 已确认决策

- **方案 C**：先独立开发 AI 聊天项目；Phase 2 再把 AI 作为服务接入 MsgRail。
- **独立目录/仓库**：`~/Linux/AI_Companion`，不放进 `Spark_Push`。
- **不碰模型底层**：厂商 API 或本地开源部署均可。
- **先手写 Agent 循环**：不一开始用 LangChain/LangGraph；框架后置。
- **SSE 用于模型输出流**；MCP 远程传输用 **Streamable HTTP**，旧版 HTTP+SSE 只作为原理了解。
- **默认技术栈**（待最终确认）：Python FastAPI + OpenAI 兼容接口（DeepSeek/Qwen）+ PostgreSQL/pgvector + Redis。

## 4. 讨论过但未采纳

- 直接在 MsgRail 里加 C++ AI 模块：C++ 的 LLM/MCP 生态薄，偏离学习目标。
- 一开始用 LangChain/LangGraph：会隐藏上下文装配、工具循环、流式解析等核心细节。
- AI 项目放进 `Spark_Push` monorepo：C++/Python 构建与约定混杂，服务边界练习打折扣。

## 5. 架构摘要

```text
浏览器 ──HTTP/SSE──> FastAPI AI 服务
                        ├─ 会话/上下文编排
                        ├─ LLM 适配层 ──> 厂商 API（OpenAI 兼容）
                        ├─ MCP Client ──> stdio / Streamable HTTP MCP Server
                        └─ PostgreSQL/pgvector + Redis
```

Phase 2：

```text
浏览器 ──WS──> MsgRail Comet ──gRPC──> Logic ──HTTP SSE / gRPC stream──> AI 服务
                                        │                                  ├─ LLM
                                        └── Kafka ──> Job ──> MySQL        └─ MCP
```

详细设计见 `01-architecture.md`、`02-tech-design.md`、`03-integration-contract.md`。

## 6. 路线图

| 阶段 | 内容 | 验收 |
|---|---|---|
| P0 | FastAPI + SSE 单轮流式 | 浏览器打字机输出，`curl -N` 可见事件 |
| P1 | 多轮 + PostgreSQL + 角色卡 | 关页面再回来能继续聊 |
| P2 | token 预算 + 滚动摘要 | 20 轮后仍记得设定 |
| P3 | 工具调用 + MCP | 模型自动调用天气/时间工具 |
| P4 | 长期记忆 + pgvector | 能回访用户之前说过的事 |
| P5 | 观测 + 限流 + 评测 | 能对比 prompt 版本效果 |
| P6 | 接入 MsgRail | IM 里给 bot 发消息，收到流式回复 |

> 2026-11-21：P0 已实现并验证。`pytest -q` 9 passed；uvicorn 实机 curl 得到
> `message_start → content_delta × 5 → usage → message_end`。浏览器端可再手动验收停止按钮。
>
> 2026-11-21：P1 已完成（SQLAlchemy + Alembic + PostgreSQL、多轮历史、幂等、前端历史恢复）。
>
> 2026-11-21：P2 已完成并验证。26 tests passed；PostgreSQL 迁移 `0002_summaries` 已应用；
> 摘要模型使用 `qwen-turbo`，上下文按 token 预算装配，历史压缩成滚动摘要。
>
> 2026-11-22：P3 第一阶段已完成。39 tests passed；迁移 `0003_tool_calls` 已应用；
> 手写 AgentLoop、ToolRegistry、本地时间工具、MCP stdio 时间 Server、Open-Meteo 真实天气已接入并验证。
> Streamable HTTP 尚未实现。

## 7. 待确认

- 后端语言：默认 Python FastAPI。
- 模型通道：默认 OpenAI 兼容（DeepSeek/Qwen）；是否同时接 Claude。
- 前端：默认极简 HTML/JS。
- 鉴权：P0 用固定 dev token，P1 再上 JWT。
- Embedding 模型：P4 再定。

## 8. 下一步

1. P3 第一阶段已验证：MCP stdio 时间、Open-Meteo 天气、AgentLoop、SSE 工具事件和审计都正常。
2. P3 第二阶段：本地 Streamable HTTP MCP Server。
3. 进入 P4：长期记忆/RAG（先解决 pgvector 安装）。
4. P5：观测与评测。

## 9. 新会话启动提示

> 先读 `docs/00-handoff.md`、`docs/01-architecture.md`、`docs/02-tech-design.md`；确认当前阶段后，再按 `CLAUDE.md` 的流程开发。
