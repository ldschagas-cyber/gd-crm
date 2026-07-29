"""Cliente MSAL (Microsoft Graph) para as integrações de E-mail/Calendário.

Autenticação por certificado, não client secret — a política do tenant
gdconecta.onmicrosoft.com bloqueia criação de client secrets (ver
docs/ESPECIFICACAO_TECNICA_V1.md §9.2).
"""
from pathlib import Path

import msal

from app.core.config import settings

GRAPH_SCOPES = {
    "email": [
        "https://graph.microsoft.com/Mail.Read",
        "https://graph.microsoft.com/Mail.Send",
        "https://graph.microsoft.com/User.Read",
    ],
    "calendario": [
        "https://graph.microsoft.com/Calendars.ReadWrite",
        "https://graph.microsoft.com/OnlineMeetings.ReadWrite",
        "https://graph.microsoft.com/User.Read",
    ],
}


def get_msal_app() -> msal.ConfidentialClientApplication:
    private_key = Path(settings.MICROSOFT_CERT_PATH).read_text()
    return msal.ConfidentialClientApplication(
        client_id=settings.MICROSOFT_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}",
        client_credential={
            "private_key": private_key,
            "thumbprint": settings.MICROSOFT_CERT_THUMBPRINT,
        },
    )
