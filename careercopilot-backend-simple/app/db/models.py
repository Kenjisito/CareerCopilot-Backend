"""
Modelos de base de datos. Un modelo por entidad, agrupados por módulo
mediante comentarios — igual que reflejan las carpetas en app/modules/.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


def gen_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    role = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------
# Módulo ATS
# ---------------------------------------------------------------------
class AtsDiagnostic(Base):
    __tablename__ = "ats_diagnostics"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)

    file_name = Column(String, nullable=True)
    score = Column(Integer, nullable=False)
    parsed_text = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    sections = Column(JSON, nullable=False)          # {contactInfo, workExperience, education, skills}
    strengths = Column(JSON, nullable=False)          # string[]
    improvements = Column(JSON, nullable=False)       # string[]
    missing_keywords = Column(JSON, nullable=False)   # string[]

    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# ---------------------------------------------------------------------
# Módulo Entrevista (necesita estado del lado servidor: el frontend solo
# envía questionId + answer, sin sessionId explícito — ver interview
# service del frontend — así que el backend debe poder resolver a qué
# sesión pertenece cada pregunta a partir de su propio id).
# ---------------------------------------------------------------------
class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)

    job_title = Column(String, nullable=False)
    category = Column(String, nullable=False)          # technical | behavioral | situational | mixed
    number_of_questions = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("InterviewQuestionRecord", back_populates="session", order_by="InterviewQuestionRecord.index")


class InterviewQuestionRecord(Base):
    __tablename__ = "interview_questions"

    id = Column(String, primary_key=True, default=gen_id)  # este id ES el "questionId" que ve el frontend
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    index = Column(Integer, nullable=False)  # posición dentro de la sesión (0-based)

    category = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    context_or_tips = Column(Text, nullable=True)

    # Se completan cuando el usuario responde (POST /interview/answer)
    answer = Column(Text, nullable=True)
    feedback_score = Column(Integer, nullable=True)
    feedback_strengths = Column(JSON, nullable=True)
    feedback_improvements = Column(JSON, nullable=True)
    feedback_suggested_answer = Column(Text, nullable=True)

    session = relationship("InterviewSession", back_populates="questions")


# ---------------------------------------------------------------------
# Historial (propuesto — el frontend hoy usa datos mock en historial/page.tsx,
# no llama a ningún servicio todavía. Se deja modelado para cuando se
# conecte, unificando referencias a AtsDiagnostic y futuros Job Match).
# ---------------------------------------------------------------------
class HistorialItem(Base):
    __tablename__ = "historial_items"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)

    tipo = Column(String, nullable=False)  # "ATS" | "Match"
    titulo = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    role = Column(String, nullable=True)

    ats_diagnostic_id = Column(String, ForeignKey("ats_diagnostics.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------
# Email (propuesto — email/page.tsx hoy es 100% estático, no llama a
# ningún servicio ni existe email-service.ts. Se deja modelado siguiendo
# el contrato ya definido en frontend/types/email.ts).
# ---------------------------------------------------------------------
class EmailGenerated(Base):
    __tablename__ = "emails_generated"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)

    recipient_name = Column(String, nullable=True)
    company_name = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    tone = Column(String, nullable=False)
    type = Column(String, nullable=False)
    additional_notes = Column(Text, nullable=True)

    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
