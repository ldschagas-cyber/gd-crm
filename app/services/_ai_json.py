"""Helper compartilhado pelos serviços que pedem à IA para responder em JSON puro
(sem markdown, sem texto ao redor) e precisam extrair esse objeto da resposta."""
import json
import re

from app.core.exceptions import ConflictError


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ConflictError("A IA não retornou uma resposta em formato válido. Tente novamente.")
    return json.loads(match.group(0))
