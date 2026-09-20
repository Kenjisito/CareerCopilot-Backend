"""Modelos SQLAlchemy compartidos por los modulos del dominio."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UsuarioModel(Base):
    __tablename__ = "usuarios"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    nombre_completo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    plan: Mapped[str] = mapped_column(String(20), default="free")
    organization_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    cvs: Mapped[list["CVModel"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    matches: Mapped[list["JobMatchModel"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    entrevistas: Mapped[list["EntrevistaModel"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    emails: Mapped[list["EmailGenerated"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")


class CVModel(Base):
    __tablename__ = "cvs"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    parsed_text: Mapped[str] = mapped_column(Text)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    usuario: Mapped[UsuarioModel] = relationship(back_populates="cvs")
    matches: Mapped[list["JobMatchModel"]] = relationship(back_populates="cv", cascade="all, delete-orphan")


class JobMatchModel(Base):
    __tablename__ = "job_matches"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    cv_id: Mapped[UUID] = mapped_column(ForeignKey("cvs.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(255))
    oferta_texto: Mapped[str] = mapped_column(Text)
    # JSON mantiene SQLite compatible. Puede migrarse a pgvector en PostgreSQL
    # cuando se habilite la extensión, sin cambiar el contrato del servicio.
    oferta_embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    score_compatibilidad: Mapped[int] = mapped_column(Integer)
    cumple: Mapped[list] = mapped_column(JSON, default=list)
    no_cumple: Mapped[list] = mapped_column(JSON, default=list)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    usuario: Mapped[UsuarioModel] = relationship(back_populates="matches")
    cv: Mapped[CVModel] = relationship(back_populates="matches")
    entrevistas: Mapped[list["EntrevistaModel"]] = relationship(back_populates="job_match", cascade="all, delete-orphan")


class EntrevistaModel(Base):
    __tablename__ = "entrevistas"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    job_match_id: Mapped[UUID] = mapped_column(ForeignKey("job_matches.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(30))
    seniority_inferido: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="activa")
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usuario: Mapped[UsuarioModel] = relationship(back_populates="entrevistas")
    job_match: Mapped[JobMatchModel] = relationship(back_populates="entrevistas")
    mensajes: Mapped[list["MensajeModel"]] = relationship(back_populates="entrevista", cascade="all, delete-orphan", order_by="MensajeModel.created_at")


class MensajeModel(Base):
    __tablename__ = "mensajes"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    entrevista_id: Mapped[UUID] = mapped_column(ForeignKey("entrevistas.id", ondelete="CASCADE"), index=True)
    rol: Mapped[str] = mapped_column(String(20))
    contenido: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    entrevista: Mapped[EntrevistaModel] = relationship(back_populates="mensajes")


class EmailGenerated(Base):
    __tablename__ = "emails_generados"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    job_match_id: Mapped[UUID | None] = mapped_column(ForeignKey("job_matches.id", ondelete="SET NULL"), nullable=True)
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    usuario: Mapped[UsuarioModel] = relationship(back_populates="emails")


User = UsuarioModel
AtsDiagnostic = CVModel
InterviewSession = EntrevistaModel
InterviewQuestionRecord = MensajeModel
HistorialItem = JobMatchModel
