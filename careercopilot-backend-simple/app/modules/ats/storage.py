import uuid
from fastapi import UploadFile, HTTPException
from app.core.supabase import supabase_admin_client

BUCKET_NAME = "cvs_almacenados"  

async def upload_cv_to_supabase(file: UploadFile, usuario_id: uuid.UUID) -> str:
    """
    Sube un CV en PDF o DOCX a Supabase Storage y retorna su URL o ruta pública.
    """
    file_bytes = await file.read()
    file_extension = file.filename.split(".")[-1].lower()
    
    # Nombre único para prevenir sobrescrituras
    file_path = f"{usuario_id}/{uuid.uuid4()}.{file_extension}"

    if supabase_admin_client is None:
        raise HTTPException(status_code=503, detail="Supabase Storage no está configurado")
    try:
        # Subida al bucket usando la API de Storage
        response = supabase_admin_client.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": file.content_type}
        )
        
        # Obtener URL del archivo
        file_url = supabase_admin_client.storage.from_(BUCKET_NAME).get_public_url(file_path)
        return file_url
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al subir el archivo a Supabase Storage: {str(e)}"
        )