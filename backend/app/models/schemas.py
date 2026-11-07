from pydantic import BaseModel, Field
from typing import List, Optional

class TaskSpec(BaseModel):
    bot: str = Field(description="배정할 봇 ID (예: curriculum, assessment, lesson, record)")
    title: str = Field(description="과업 제목")
    deliverable: str = Field(description="구체적 산출물 형태 및 분량")
    depends_on: List[str] = Field(default_factory=list, description="선행해야 하는 bot_id 목록 (예: ['curriculum'])")

class DispatchPlan(BaseModel):
    summary: str = Field(description="요청 요약")
    unit: str = Field(description="관련 단원 (예: 3과)")
    tasks: List[TaskSpec] = Field(description="세부 과업 목록 (1~4개)")
    approval_question: str = Field(description="교사가 예/아니오로 답할 수 있는 결재 질문")
    course_code: Optional[str] = Field(default=None, description="과목 코드 (예: ENG1, ADV_ENG1 등)")
    clarification: Optional[str] = Field(default=None, description="전체 교무회의 등에서 과목을 특정할 수 없을 때 되묻는 안내 질문")

class RequestCreate(BaseModel):
    content: str

class ApprovalDecision(BaseModel):
    decision: str = Field(description="approved 또는 rejected")
    reason: Optional[str] = Field(default=None, description="반려 사유 (반려 시 필수)")

class ContextNoteCreate(BaseModel):
    course_code: str
    unit: str
    kind: str = Field(description="본문, 진도, 성취기준, 차시기록 중 하나")
    content: str

class StudentCreate(BaseModel):
    course_code: str
    class_no: int
    student_no: int
    name: str
