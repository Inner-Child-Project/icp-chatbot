import operator
from typing import Annotated, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

from .models import ExtractedLead
from .prompts import EXTRACTION_PROMPT, PROPOSAL_PROMPT, SYSTEM_PROMPT
from .state import LeadInfo, LeadState


def _make_llm():
    import os

    return ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.4,
        max_tokens=500,
    )


llm = _make_llm()
extraction_llm = llm.with_structured_output(ExtractedLead)


async def chat_node(state: LeadState) -> dict:
    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
    ])
    return {"messages": [response]}


async def extract_info_node(state: LeadState) -> dict:
    convo_text = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in state["messages"]
        if m.content
    )
    result: ExtractedLead = await extraction_llm.ainvoke([
        SystemMessage(content=EXTRACTION_PROMPT),
        HumanMessage(content=convo_text),
    ])

    current = dict(state.get("lead_info") or {})
    for field in ("name", "email", "phone", "business_type", "problem_description", "urgency", "budget_range"):
        val = getattr(result, field, None)
        if val and not current.get(field):
            current[field] = val

    has_required = bool(current.get("name")) and bool(current.get("email")) and bool(current.get("problem_description"))
    return {"lead_info": current, "info_complete": has_required}


async def generate_proposal_node(state: LeadState) -> dict:
    info = state.get("lead_info", {})
    context = "\n".join(f"{k}: {v}" for k, v in info.items() if v)

    response = await llm.ainvoke([
        SystemMessage(content=PROPOSAL_PROMPT),
        HumanMessage(content=f"Lead info:\n{context}"),
    ])
    proposal_text = response.content
    confirmation = AIMessage(content=(
        f"{proposal_text}\n\n"
        "Does this look right to you? Reply **yes** to proceed, "
        "or tell me what you'd like me to adjust."
    ))
    return {
        "proposal": proposal_text,
        "messages": [confirmation],
    }


async def review_proposal_node(state: LeadState) -> dict:
    """Interrupt: pause here until the user approves or requests changes."""
    feedback = interrupt({
        "question": "Are you satisfied with this proposal?",
    })

    feedback_lower = str(feedback).lower().strip()
    positive_signals = [
        "yes", "yeah", "yep", "yup", "ok", "okay", "sure",
        "good", "great", "perfect", "love", "sounds good", "go ahead", "approved",
    ]

    if any(w in feedback_lower for w in positive_signals):
        return {"proposal_approved": True}

    return {
        "proposal_approved": False,
        "info_complete": False,
        "messages": [HumanMessage(content=str(feedback))],
    }


async def submit_lead_node(state: LeadState) -> dict:
    import httpx
    import os

    info = state.get("lead_info", {})
    webhook_url = os.getenv("N8N_LEAD_WEBHOOK_URL", "")
    if not webhook_url:
        return {"submitted": False}

    payload = {
        "name": info.get("name", ""),
        "email": info.get("email", ""),
        "phone": info.get("phone", ""),
        "sourceForm": "chatbot",
        "message": info.get("problem_description", ""),
        "consentTextVersion": "v1",
        "proposalText": state.get("proposal", ""),
        "businessType": info.get("business_type", ""),
        "urgency": info.get("urgency", ""),
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=payload, timeout=10)
            submitted = resp.status_code == 200
    except Exception:
        submitted = False

    confirmation = AIMessage(content=(
        "✅ All done! Your information has been sent to our team. "
        "Expect a call or email within one business day. Thanks for reaching out!"
    ))
    return {"submitted": submitted, "messages": [confirmation]}


def route_after_chat(state: LeadState) -> Literal["extract_info", "__end__"]:
    messages = state.get("messages", [])
    if not messages or len(messages) > 30:
        return "__end__"
    last = messages[-1]
    if isinstance(last, AIMessage):
        return "__end__"
    return "extract_info"


def route_after_extract(state: LeadState) -> Literal["generate_proposal", "__end__"]:
    if state.get("info_complete"):
        return "generate_proposal"
    return "__end__"


def route_after_proposal(state: LeadState) -> Literal["review_proposal", "__end__"]:
    if state.get("proposal"):
        return "review_proposal"
    return "__end__"


def route_after_review(state: LeadState) -> Literal["submit_lead", "chat_node"]:
    if state.get("proposal_approved"):
        return "submit_lead"
    return "chat_node"


def build_graph():
    builder = StateGraph(LeadState)

    builder.add_node("chat_node", chat_node)
    builder.add_node("extract_info", extract_info_node)
    builder.add_node("generate_proposal", generate_proposal_node)
    builder.add_node("review_proposal", review_proposal_node)
    builder.add_node("submit_lead", submit_lead_node)

    builder.add_edge(START, "chat_node")
    builder.add_conditional_edges("chat_node", route_after_chat, ["extract_info", "__end__"])
    builder.add_conditional_edges("extract_info", route_after_extract, ["generate_proposal"])
    builder.add_edge("generate_proposal", "review_proposal")
    builder.add_conditional_edges("review_proposal", route_after_review, ["submit_lead", "chat_node"])
    builder.add_edge("submit_lead", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)
