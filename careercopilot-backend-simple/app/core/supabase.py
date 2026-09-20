"""Clientes Supabase opcionales para Storage y operaciones administrativas."""
from supabase import Client, create_client
from app.core.config import settings

# Cliente estándar con clave pública (Anon key)
supabase_client: Client | None = (
    create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    if settings.SUPABASE_URL and settings.SUPABASE_KEY else None
)

# Cliente administrativo con Service Role (Uso exclusivo interno/backend)
supabase_admin_client: Client | None = (
    create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY else None
)