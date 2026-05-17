from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from config import Settings, get_settings
from kb.retrieval import kb_system_prompt, log_llm_prompt, retrieve_for_qa
from mcp_service.commerce_stubs import stub_kb_answer

from .intent import route_intent
from .mcp_tools import call_mcp_tool


class ChatbotState(TypedDict, total=False):
    uid: str
    conversation_id: str
    user_text: str
    history: list[dict[str, Any]]
    route: Literal["knowledge", "order", "logistics", "human"]
    reply: str


def _history_snippet(history: list[dict[str, Any]], max_chars: int = 2000) -> str:
    lines: list[str] = []
    for m in history:
        role = m.get("role", "")
        content = str(m.get("content", ""))
        lines.append(f"{role}: {content}")
    text = "\n".join(lines)
    return text[-max_chars:]


async def intent_node(state: ChatbotState) -> dict[str, Any]:
    return {"route": route_intent(state.get("user_text", ""))}


@lru_cache(maxsize=4)
def _tongyi_client(*, api_key: str, model: str) -> Any:
    """Reuse one ChatTongyi instance per (api_key, model) to avoid per-request client setup."""
    from langchain_community.chat_models.tongyi import ChatTongyi

    return ChatTongyi(model=model, dashscope_api_key=api_key, streaming=False)


def _history_for_llm(history: list[dict[str, Any]], user_text: str) -> list[dict[str, Any]]:
    """Avoid duplicating the latest user turn when building LLM messages."""
    if not history:
        return []
    last = history[-1]
    if last.get("role") == "user" and str(last.get("content", "")) == user_text:
        return history[:-1]
    return history


async def knowledge_node(state: ChatbotState) -> dict[str, Any]:
    settings: Settings = get_settings()
    user_text = state.get("user_text", "")
    history = state.get("history") or []
    prior = _history_for_llm(history, user_text)
    snippet = _history_snippet(prior)

    if not settings.dashscope_api_key:
        reply = await stub_kb_answer(question=user_text, history_snippet=snippet)
        return {"reply": reply}

    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        chunks = await retrieve_for_qa(
            user_text,
            conversation_id=state.get("conversation_id"),
            uid=state.get("uid"),
            settings=settings,
        )
        system_content = kb_system_prompt(chunks)
        log_llm_prompt(
            conversation_id=state.get("conversation_id"),
            uid=state.get("uid"),
            system_content=system_content,
            history=prior,
            user_text=user_text,
        )

        msgs: list[Any] = [SystemMessage(content=system_content)]
        for m in prior:
            c = str(m.get("content", ""))
            if m.get("role") == "user":
                msgs.append(HumanMessage(content=c))
            elif m.get("role") == "assistant":
                msgs.append(AIMessage(content=c))
        msgs.append(HumanMessage(content=user_text))
        model = _tongyi_client(api_key=settings.dashscope_api_key, model=settings.llm_model)
        res = await model.ainvoke(msgs)
        reply = str(getattr(res, "content", res))
    except Exception:
        reply = await stub_kb_answer(question=user_text, history_snippet=snippet)

    return {"reply": reply}


async def order_node(state: ChatbotState) -> dict[str, Any]:
    data = await call_mcp_tool("order_get", {"order_id": None, "uid": state.get("uid")})
    reply = f"{data['message']}\n示例字段：{data.get('sample')}"
    return {"reply": reply}


async def logistics_node(state: ChatbotState) -> dict[str, Any]:
    data = await call_mcp_tool(
        "logistics_track",
        {"tracking_no": None, "order_id": None},
    )
    reply = f"{data['message']}\n示例字段：{data.get('sample')}"
    return {"reply": reply}


async def human_node(state: ChatbotState) -> dict[str, Any]:
    data = await call_mcp_tool(
        "human_escalate",
        {"reason": state.get("user_text"), "uid": state.get("uid")},
    )
    reply = f"{data['message']}\n工单号：{data.get('ticket_id')}"
    return {"reply": reply}


def _route_edge(state: ChatbotState) -> str:
    r = state.get("route") or "knowledge"
    if r in ("knowledge", "order", "logistics", "human"):
        return r
    return "knowledge"


def build_chatbot_graph() -> Any:
    g = StateGraph(ChatbotState)
    g.add_node("intent", intent_node)
    g.add_node("knowledge", knowledge_node)
    g.add_node("order", order_node)
    g.add_node("logistics", logistics_node)
    g.add_node("human", human_node)

    g.add_edge(START, "intent")
    g.add_conditional_edges(
        "intent",
        _route_edge,
        {
            "knowledge": "knowledge",
            "order": "order",
            "logistics": "logistics",
            "human": "human",
        },
    )
    g.add_edge("knowledge", END)
    g.add_edge("order", END)
    g.add_edge("logistics", END)
    g.add_edge("human", END)
    return g.compile()


_graph = build_chatbot_graph()


def get_compiled_graph() -> Any:
    return _graph
