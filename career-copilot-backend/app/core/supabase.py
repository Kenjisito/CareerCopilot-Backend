from __future__ import annotations

"""Creación del cliente async de Supabase para el ciclo de vida de la API."""
from httpx import AsyncClient as HttpxAsyncClient
from supabase import AsyncClient, acreate_client
from supabase.lib.client_options import AsyncClientOptions

from app.core.config import settings


async def create_supabase_client() -> tuple[AsyncClient, HttpxAsyncClient]:
    http_client = HttpxAsyncClient()
    options = AsyncClientOptions(
        auto_refresh_token=False,
        persist_session=False,
        httpx_client=http_client,
    )
    client = await acreate_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
        options=options,
    )
    return client, http_client