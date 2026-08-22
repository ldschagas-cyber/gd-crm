"""ContadorService — pedido de emissão de NF ao contador no faturamento.

O sistema NÃO emite NFS-e (isso é do contador — decisão de escopo/chancela #7). Ele
apenas AUTOMATIZA o handoff: no faturamento, monta um e-mail consolidado com as cobranças
que ainda precisam de NF e envia ao contador via Microsoft Graph (a partir de uma mailbox
conectada). Desacoplado: falha de e-mail nunca derruba o faturamento. Config por tenant em
Tenant.config["financeiro"]: contador_email, contador_nf_enabled, contador_remetente_id.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import get_current_tenant, get_current_user_id
from app.core.money import money
from app.models.billing import Cobranca
from app.models.tenant import Tenant
from app.repositories.company import CompanyRepository


class ContadorEmailResult:
    def __init__(self, enviado: bool, solicitadas: int, aviso: str | None = None):
        self.enviado = enviado
        self.solicitadas = solicitadas
        self.aviso = aviso


class ContadorService:
    def __init__(self, db: Session):
        self.db = db
        self.companies = CompanyRepository(db)

    def _config(self) -> dict:
        tenant = self.db.get(Tenant, get_current_tenant())
        cfg = (tenant.config or {}) if tenant else {}
        return cfg.get("financeiro", {}) or {}

    def solicitar_nf(self, cobrancas: list[Cobranca], competencia: str) -> ContadorEmailResult:
        """Envia um único e-mail ao contador com as cobranças que precisam de NF e marca
        cada uma como solicitada. Retorna aviso (sem enviar) quando não há config/mailbox."""
        pendentes = [c for c in cobrancas if c.nf_solicitada_em is None and c.nf_numero is None]
        if not pendentes:
            return ContadorEmailResult(False, 0)

        cfg = self._config()
        if not cfg.get("contador_nf_enabled", True):
            return ContadorEmailResult(False, 0, "Pedido de NF ao contador desativado nas configurações")
        contador_email = (cfg.get("contador_email") or "").strip()
        if not contador_email:
            return ContadorEmailResult(False, 0, "E-mail do contador não configurado")

        remetente_id = cfg.get("contador_remetente_id") or get_current_user_id()
        if remetente_id is None:
            return ContadorEmailResult(False, 0, "Nenhuma mailbox (remetente) definida para o envio")

        subject = f"[Argos] Emissão de NF — competência {competencia}"
        body = self._montar_corpo(pendentes, competencia)
        try:
            # Import tardio: evita dependência dura do Graph no caminho de faturamento.
            from app.services.graph_client import GraphClient
            GraphClient(self.db).send_mail(UUID(str(remetente_id)), contador_email, subject, body)
        except Exception:
            return ContadorEmailResult(
                False, 0,
                "Não foi possível enviar ao contador (mailbox não conectada?). "
                "As cobranças seguem sem NF — reenvie pela tela de Faturamento.",
            )

        agora = datetime.now(timezone.utc)
        for c in pendentes:
            c.nf_solicitada_em = agora
        self.db.flush()
        return ContadorEmailResult(True, len(pendentes))

    def _montar_corpo(self, cobrancas: list[Cobranca], competencia: str) -> str:
        nomes: dict[UUID, str] = {}
        linhas = []
        total = money(0)
        for c in cobrancas:
            if c.company_id not in nomes:
                empresa = self.companies.get(c.company_id)
                nomes[c.company_id] = (
                    (empresa.nome_fantasia or empresa.razao_social) if empresa else str(c.company_id)
                )
            total += money(c.valor)
            linhas.append(
                f"- {nomes[c.company_id]} | {c.descricao} | venc. {c.vencimento:%d/%m/%Y} "
                f"| R$ {money(c.valor)}"
            )
        return (
            f"Olá,\n\nSeguem as cobranças da competência {competencia} que precisam de NF:\n\n"
            + "\n".join(linhas)
            + f"\n\nTotal: R$ {total}\nQuantidade: {len(cobrancas)} cobrança(s)."
            + "\n\nMensagem gerada automaticamente pelo Argos (GD Conecta)."
        )
