from __future__ import annotations
import uuid
from fastapi import UploadFile
from supabase import AsyncClient

BUCKET_NAME = "cvs_almacenados"  

async def upload_cv_to_supabase(file: UploadFile, usuario_id: uuid.UUID, supabase: AsyncClient) -> str:
    """
    Sube un CV en PDF o DOCX a Supabase Storage y retorna su URL o ruta pública.
    """
    file_bytes = await file.read()
    file_extension = (file.filename or "cv").split(".")[-1].lower()
    
    # Nombre único para prevenir sobrescrituras
    file_path = f"{usuario_id}/{uuid.uuid4()}.{file_extension}"

    await supabase.storage.from_(BUCKET_NAME).upload(
        path=file_path,
        file=file_bytes,
        file_options={"content-type": file.content_type or "application/octet-stream"},
    )
    return supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)