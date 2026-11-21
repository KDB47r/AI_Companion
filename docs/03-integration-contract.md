# 03 · Phase 2 集成契约（AI Companion ↔ MsgRail）

> 状态：草案。Phase 2 才实现；先定义契约，避免两个仓库各自演化后对不上。

## 1. 目标

把 AI Companion 作为 MsgRail 里的一个“AI 用户”：

```text
浏览器 ──WebSocket──> Comet ──gRPC──> Logic ──HTTP SSE / gRPC──> AI Companion
                                        │                         ├─ LLM
                                        └── Kafka ──> Job ──> MySQL
```

- MsgRail 负责连接、鉴权、路由、持久化。
- AI Companion 只负责生成，不碰 IM 连接管理。
- 两边通过内部接口契约解耦。

## 2. 方案对比

| 方案 | 优点 | 缺点 | 建议 |
|---|---|---|---|
| HTTP + SSE（内部） | 复用 P0 实现，调试简单 | 需要把 SSE 转成 WS 帧 | **首选** |
| gRPC stream | 类型强、性能好、适合内部服务 | 要改 proto、调试成本高 | P6 稳定后再考虑 |

先做 HTTP SSE，契约设计成可平移到 gRPC。

## 3. 接口定义

### 3.1 `POST /internal/v1/agent/stream`

请求头：

```text
Authorization: Bearer <INTERNAL_TOKEN>
Content-Type: application/json
Accept: text/event-stream
Idempotency-Key: <msg_id>
```

请求体：

```json
{
  "request_id": "uuid",
  "user_id": "u_123",
  "conversation_id": "c_456",
  "message_id": "m_789",
  "message": "你好",
  "persona_id": "default"
}
```

字段说明：

- `user_id` / `conversation_id` / `message_id`：MsgRail 侧的 ID，AI 服务按外部 ID 存储映射。
- `message_id` 同时作为 `Idempotency-Key`，重试不会产生两条 AI 回复。
- `persona_id`：MsgRail 侧选择的 AI 角色。

响应：`text/event-stream`，事件与公共 SSE 协议一致，额外字段：

```text
event: message_start
data: {"ai_message_id":"m_ai_01","conversation_id":"c_456","reply_to":"m_789"}

event: content_delta
data: {"delta":"你好呀"}

event: tool_call
data: {"call_id":"call_01","name":"get_weather","arguments":{"city":"杭州"}}

event: tool_result
data: {"call_id":"call_01","status":"ok","preview":"晴，26℃"}

event: message_end
data: {"finish_reason":"stop","ai_message_id":"m_ai_01","usage":{"input_tokens":1200,"output_tokens":80}}
```

## 4. 事件到 MsgRail WS 帧的映射

MsgRail 的 Logic 读取 SSE 后，转换成现有 WebSocket 下行帧。建议帧类型：

| SSE event | WS 帧 | 字段 |
|---|---|---|
| `message_start` | `ai_stream_start` | `request_id`, `ai_message_id`, `reply_to` |
| `content_delta` | `ai_stream_delta` | `request_id`, `delta` |
| `tool_call` | `ai_stream_tool` | `request_id`, `call_id`, `name`, `status=started` |
| `tool_result` | `ai_stream_tool` | `request_id`, `call_id`, `status=ok/error` |
| `message_end` | `ai_stream_end` | `request_id`, `finish_reason`, `usage` |
| `error` | `ai_stream_error` | `request_id`, `code`, `message`, `retryable` |

具体封装要适配 MsgRail 现有 WS 消息结构；如果已有通用 `push` 帧，可直接复用，不新增类型。

## 5. ID 映射

| 概念 | MsgRail | AI Companion |
|---|---|---|
| 用户 | `user_id` | `users.external_id` |
| 会话 | `conversation_id` | `conversations.id`（直接用外部 ID） |
| 用户消息 | `message_id` | `messages.external_message_id` + `client_message_id` |
| AI 回复 | 新消息 ID | `messages.id`（`ai_message_id`） |
| 请求链路 | `request_id` | `runs.id`（或单独 `request_id` 字段） |

实现建议：

- AI 服务允许 `conversations.id` 直接使用 MsgRail 的会话 ID（字符串）。
- `messages.external_message_id` 存 MsgRail 消息 ID；唯一索引。
- 重试时按 `(conversation_id, client_message_id)` 幂等命中已有 AI 消息。

## 6. 鉴权与网络

- 内部接口**不暴露公网**；只允许 MsgRail 所在网段访问。
- `Authorization: Bearer <INTERNAL_TOKEN>`；token 定期轮换。
- 生产可升级 mTLS；不要把用户级 JWT 传给 AI 服务。
- AI 服务的 Provider Key 只存在 AI 服务侧，MsgRail 不接触。

## 7. 幂等与重试

- Logic 用 `message_id` 作为 `Idempotency-Key`。
- 重试策略：
  - **首 token 之前失败**：可安全重试。
  - **首 token 之后断流**：不要重新生成整段，先尝试 `Last-Event-ID` 续传；失败则把已收到部分作为最终消息，并标记中断。
- AI 服务对重复请求：
  - 已完成：返回已有消息（`message_end` 带 `replayed=true`）。
  - 进行中：返回 `409 AI_REQUEST_IN_PROGRESS`，Logic 可选择等待或提示稍后。
- 确保用户只看到一条 AI 回复。

## 8. 取消

- 用户在 IM 里点“停止”或断开连接 → Logic 取消 HTTP 请求。
- AI 服务检测断开 → 取消上游模型请求 → 部分结果标 `aborted` 落库。
- 已推送的 WS 帧不回滚；前端把消息标为“已停止”。

## 9. 错误码

| 错误码 | HTTP | 含义 | Logic 处理 |
|---|---|---|---|
| `AI_INVALID_REQUEST` | 400 | 参数错误 | 不重试，记录日志 |
| `AI_UNAUTHORIZED` | 401 | 内部 token 错 | 告警 |
| `AI_RATE_LIMITED` | 429 | AI 服务/上游限流 | 退避重试或提示 |
| `AI_CONTENT_BLOCKED` | 422 | 内容审核命中 | 返回固定提示 |
| `AI_UPSTREAM_TIMEOUT` | 504 | 模型超时 | 可重试 |
| `AI_UPSTREAM_UNAVAILABLE` | 503 | 模型/服务不可用 | 可重试 + 降级提示 |
| `AI_INTERNAL` | 500 | 未预期错误 | 记录 request_id，告警 |
| `STREAM_EXPIRED` | 409 | 重连缓冲过期 | 用幂等键重新请求 |

## 10. 可靠性与降级

- AI 服务不可用：Logic 发送固定提示“AI 暂时不可用，请稍后再试”，不阻塞 IM 主流程。
- 上游限流：AI 服务返回 `AI_RATE_LIMITED`，Logic 可排队或提示。
- 超时：默认 120s；超过则中断并提示。
- 日志：两边都记录 `request_id`，便于跨服务追踪。
- 监控：AI 服务暴露 `/metrics`（P5），MsgRail 侧记录调用耗时/错误率。

## 11. 版本化

- 路径带版本：`/internal/v1/...`。
- 只做增量字段；删除/改语义必须升 `v2`。
- 事件类型新增时，旧客户端忽略未知事件。
- 契约变更同步更新本文件，并在两个仓库的 PR 中互相引用。

## 12. 验收标准

1. 在 IM 里给 AI 用户发消息，浏览器收到逐段流式回复。
2. 工具调用时，前端能看到“正在调用工具”的状态，结束后继续输出。
3. 点“停止”能中断，已输出部分保留。
4. 同一 `message_id` 重试不会产生两条 AI 回复。
5. AI 服务挂掉时，IM 仍能正常收发其他消息，AI 会话显示友好提示。
6. 断线重连后，未完成的回复可通过 `Last-Event-ID` 续传（或明确提示已中断）。
