import operator
import re
from typing import Annotated, Literal, Optional

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

from .models import ExtractedLead
from .prompts import EXTRACTION_PROMPT, PROPOSAL_PROMPT, SYSTEM_PROMPT
from .state import LeadInfo, LeadState

load_dotenv()


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
        # Normalize LLM "null"/"none"/"" strings to None (models often return the literal string)
        if isinstance(val, str) and val.strip().lower() in ("null", "none", ""):
            val = None
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
        "proposal": state.get("proposal", ""),
    })

    feedback_lower = str(feedback).lower().strip()

    # Negative signals take priority — "no, add X" is a rejection even if it
    # contains a substring like "ok" (e.g. inside "booking").
    negative_signals = [
        "no", "not", "don't", "dont", "change", "adjust", "add", "different",
        "more", "instead", "revision", "fix", "update", "actually", "rather",
    ]
    positive_signals = [
        "yes", "yeah", "yep", "yup", "ok", "okay", "sure", "good", "great",
        "perfect", "love", "approved", "proceed", "go ahead", "sounds good",
    ]

    def has_word(text, word):
        return re.search(rf"\b{re.escape(word)}\b", text) is not None

    has_negative = any(has_word(feedback_lower, w) for w in negative_signals)
    has_positive = any(has_word(feedback_lower, w) for w in positive_signals)

    if has_positive and not has_negative:
        return {"proposal_approved": True}

    return {
        "proposal_approved": False,
        "info_complete": False,
        "proposal": "",
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
            resp = await client.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                },
            )
            submitted = resp.status_code == 200
    except Exception:
        submitted = False

    if submitted:
        confirmation = AIMessage(content=(
            "✅ All done! Your information has been sent to our team. "
            "Expect a call or email within one business day. Thanks for reaching out!"
        ))
    else:
        confirmation = AIMessage(content=(
            "Thanks for sharing your details! A team member will follow up with you shortly. "
            "If you'd like to reach us right away, email hello@innerchildproject.us."
        ))
    return {"submitted": submitted, "messages": [confirmation]}


def route_after_extract(state: LeadState) -> Literal["generate_proposal", "end"]:
    if state.get("info_complete") and not state.get("proposal"):
        return "generate_proposal"
    return "end"


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
    builder.add_edge("chat_node", "extract_info")
    builder.add_conditional_edges(
        "extract_info",
        route_after_extract,
        {"generate_proposal": "generate_proposal", "end": END},
    )
    builder.add_edge("generate_proposal", "review_proposal")
    builder.add_conditional_edges(
        "review_proposal",
        route_after_review,
        {"submit_lead": "submit_lead", "chat_node": "chat_node"},
    )
    builder.add_edge("submit_lead", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)
