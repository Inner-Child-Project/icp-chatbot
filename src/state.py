from typing_extensions import TypedDict, Annotated
from typing import Optional
import operator


class LeadInfo(TypedDict, total=False):
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    business_type: Optional[str]
    problem_description: str
    urgency: str
    budget_range: Optional[str]


class LeadState(TypedDict):
    messages: Annotated[list, operator.add]
    lead_info: LeadInfo
    info_complete: bool
    proposal: str
    proposal_approved: Optional[bool]
    ready_to_submit: bool
    submitted: bool
