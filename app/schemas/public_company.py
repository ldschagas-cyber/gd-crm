"""Schemas de Buscar Empresas — proxy de busca sobre a API pública do minha-receita."""
from pydantic import BaseModel


class PublicCompanyResult(BaseModel):
    cnpj: str
    razao_social: str
    nome_fantasia: str | None = None
    uf: str | None = None
    municipio: str | None = None
    cnae_fiscal: str | None = None
    cnae_fiscal_descricao: str | None = None
    porte: str | None = None
    situacao_cadastral: str | None = None
    capital_social: float | None = None
    ja_cadastrado: bool = False


class PublicCompanySearchResponse(BaseModel):
    data: list[PublicCompanyResult]
    cursor: str | None = None


class PublicCompanyBulkAddItem(BaseModel):
    cnpj: str
    razao_social: str
    uf: str | None = None
    cnae_fiscal_descricao: str | None = None


class PublicCompanyBulkAddRequest(BaseModel):
    empresas: list[PublicCompanyBulkAddItem]


class PublicCompanyBulkAddResponse(BaseModel):
    criados: int
    ignorados: int
