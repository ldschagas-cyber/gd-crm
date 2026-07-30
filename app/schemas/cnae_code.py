"""Schemas de referência CNAE (§ Buscar Empresas)."""
from app.schemas.common import ORMModel


class CnaeCodeRead(ORMModel):
    codigo: str
    descricao: str
    secao: str
    divisao: str
    grupo: str
    classe: str
