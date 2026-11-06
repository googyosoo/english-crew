from pydantic import BaseModel, Field
from typing import List, Optional

class TaskSpec(BaseModel):
    bot: str = Field(description="배정할 봇 ID (예: assessment)")
    title: str = Field(description="과업 제목")
    deliverable: str = Field(description="구체적 산출물 형태 및 분량")

class DispatchPlan(BaseModel):
    summary: str = Field(description="요청 요약")
    unit: str = Field(description="관련 단원 (예: 3과)")
    tasks: List[TaskSpec] = Field(description="세부 과업 목록 (1~4개)")
    approval_question: str = Field(description="교사가 예/아니오로 답할 수 있는 결재 질문")

class RequestCreate(BaseModel):
    content: str

class ApprovalDecision(BaseModel):
    decision: str = Field(description="approved 또는 rejected")
    reason: Optional[str] = Field(default=None, description="반려 사유 (반려 시 필수)")
