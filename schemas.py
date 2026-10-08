from typing import Literal
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    signal: str = Field(description="What was found, e.g. 'Sender uses a free Gmail address'")
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    source_tool: str = Field(description="Which check found it")


class LLMOutput(BaseModel):
    evidence: list[Evidence]
    advice: str = Field(description="What the student should do next, 2-3 sentences")


class ScamReport(BaseModel):
    verdict: Literal["LIKELY_SCAM", "SUSPICIOUS", "LIKELY_GENUINE"]
    risk_score: int = Field(ge=0, le=100)
    evidence: list[Evidence]
    advice: str


class SecondOpinion(BaseModel):
    is_suspicious: bool
    reason: str = Field(description="One sentence explaining why")    

class ExtractedInfo(BaseModel):
    company_name: str = Field(default="", description="Company the sender claims to represent, or empty string if none")
    asks_for_money: bool = Field(description="True only if the sender demands payment from the candidate. False if the text only warns against paying.")
    asks_for_documents: bool = Field(description="True if the sender asks for ID, bank details, or similar personal documents")
    sender_type: Literal["company_hr", "agency_or_platform", "individual", "unknown"]