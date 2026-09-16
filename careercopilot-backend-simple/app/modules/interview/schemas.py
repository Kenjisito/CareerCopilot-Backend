from typing import Literal, Optional

from pydantic import BaseModel

QuestionCategory = Literal["technical", "behavioral", "situational"]


class InterviewSessionConfig(BaseModel):
    jobTitle: str
    category: Literal["technical", "behavioral", "situational", "mixed"]
    numberOfQuestions: int


class InterviewQuestion(BaseModel):
    id: str
    category: QuestionCategory
    question: str
    contextOrTips: Optional[str] = None


class AnswerFeedback(BaseModel):
    score: int
    strengths: list[str]
    areasForImprovement: list[str]
    suggestedAnswer: str


class SubmitAnswerPayload(BaseModel):
    questionId: str
    answer: str


class SubmitAnswerResult(BaseModel):
    feedback: AnswerFeedback
    nextQuestion: Optional[InterviewQuestion] = None
