#!/usr/bin/env python3
"""Debug: test what the extraction LLM returns for a name-less, email-less convo."""
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI

from src.models import ExtractedLead
from src.prompts import EXTRACTION_PROMPT

llm = ChatOpenAI(
    model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
    openai_api_key=os.getenv("OPENROUTER_API_KEY", ""),
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0.0,
    max_tokens=300,
)
extractor = llm.with_structured_output(ExtractedLead)

convo = [
    ("user", "I run a med spa in Miami and need more bookings"),
    ("assistant", "That's great! What's your name and email so a team member can follow up?"),
]

convo_text = "\n".join(f"{'User' if r == 'user' else 'Assistant'}: {m}" for r, m in convo)

result = extractor.invoke([
    SystemMessage(content=EXTRACTION_PROMPT),
    HumanMessage(content=convo_text),
])

print("=== ExtractedLead ===")
print(repr(result))
print()
print("name:", repr(result.name))
print("email:", repr(result.email))
print("problem:", repr(result.problem_description))
