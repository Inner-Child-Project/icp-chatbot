from typing import Optional

from pydantic import BaseModel


class ExtractedLead(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    business_type: Optional[str] = None
    problem_description: str = ""
    urgency: Optional[str] = None
    budget_range: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    resume_value: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str = ""
    info_complete: bool = False
    proposal: Optional[str] = None
    submitted: bool = False
    awaiting_approval: bool = False


class LeadSubmission(BaseModel):
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    sourceForm: str = "chatbot"
    message: str
    consentTextVersion: str = "v1"
    proposalText: Optional[str] = None
