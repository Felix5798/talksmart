# 电商智能客服（骨架）

Vue3 前端 + FastAPI 后端 + LangGraph 编排 + MongoDB 多轮滑动窗口 + MCP（订单/物流/转人工 stub）。

**存储层**：会话读写使用 **Motor（异步 Mongo）**，在 `async` 路由与 LangGraph 节点中直接 `await`，与 SSE 流式一致。

## 目录

- `backend/` — `api/`（FastAPI）、`graph/`（LangGraph / 意图 / 会话 / MCP 调用）、`mcp_service/`（MCP 与 stub）、`config/`、`run/`（MCP、Chroma UI、知识库入库等启动脚本）
- `frontend/` — Vue3 + Vite

## 环境变量

在 `backend/.env` 中配置（可参考 `backend/.env.example`）：

- `DASHSCOPE_API_KEY` — 可选；未配置时知识类走占位文案
- `MONGODB_URI` / `MONGODB_DB` — 会话与消息（默认库名 `ecommerce_chatbot`）
- `DATABASE_URL` — 预留 MySQL，当前骨架未使用
- `MCP_STREAMABLE_HTTP_URL` — 订单/物流/转人工走 MCP 的地址，默认 `http://127.0.0.1:8200/mcp`（需先启动 `run/run_mcp_http.py`）

**勿将真实密钥提交到 Git。**

## 后端依赖（首次）

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # 按需编辑 Mongo、MCP URL 等
```

## 本地启动（两个后端进程）

对话 API 会 **HTTP 调用** 独立 MCP（默认 8200），因此需要 **同时** 起：

1. **Commerce MCP（Streamable HTTP，8200）**

```powershell
cd backend
$env:PYTHONPATH = (Resolve-Path .).Path
python run/run_mcp_http.py
```

2. **FastAPI（8100）**

```powershell
cd backend
$env:PYTHONPATH = (Resolve-Path .).Path
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8100
```

健康检查：<http://127.0.0.1:8100/api/health>

## MCP：stdio（可选，给 Cursor）

与 8200 的 HTTP MCP **共用** `mcp_service.commerce_mcp` 里的工具定义；stdio 不占用 8200。

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path
python run/run_mcp.py
```

**Cursor MCP 示例**（`command` 改为本机 venv 的 `python.exe`）：

```json
{
  "mcpServers": {
    "ecommerce-commerce": {
      "command": "D:\\DevelopProject\\talksmart\\.venv\\Scripts\\python.exe",
      "args": ["D:\\DevelopProject\\talksmart\\backend\\run\\run_mcp.py"],
      "cwd": "D:\\DevelopProject\\talksmart\\backend",
      "env": {
        "PYTHONPATH": "D:\\DevelopProject\\talksmart\\backend"
      }
    }
  }
}
```

## 前端

```bash
cd frontend
npm install
npm run dev
```

开发时 Vite 将 `/api` 代理到 `http://127.0.0.1:8100`。

## 意图路由（占位）

关键词：`人工/转人工` → 转人工；`物流/快递` → 物流；`订单` → 订单；否则 → 知识问答（可接百炼或 stub）。

## API

- `POST /api/chat/stream` — SSE：`meta`（含 `conversation_id`）、`token`、`done`
- `GET /api/conversations?uid=1001`
- `DELETE /api/conversations/{conversation_id}?uid=1001`
- `GET /api/conversations/{conversation_id}/messages?uid=1001`
