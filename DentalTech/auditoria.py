"""Registro de auditoria (LGPD) — use `registrar(...)` nas views."""
import logging

from .models import (
    Agendamento,
    Atendimento,
    Dente,
    LogAuditoria,
    Odontograma,
    Paciente,
    Prontuario,
    Tratamento,
)

logger = logging.getLogger(__name__)


def _paciente_de(objeto):
    """Descobre a qual paciente um registro pertence (para filtrar o log)."""
    if isinstance(objeto, Paciente):
        return objeto
    if isinstance(objeto, (Agendamento, Prontuario, Odontograma)):
        return objeto.paciente
    if isinstance(objeto, Atendimento):
        return objeto.agendamento.paciente
    if isinstance(objeto, (Dente, Tratamento)):
        return objeto.odontograma.paciente
    return None


def _ip(request):
    return request.META.get("REMOTE_ADDR") if request is not None else None


def registrar(
    request,
    acao,
    objeto=None,
    *,
    paciente=None,
    campos=None,
    detalhes="",
    modelo="",
    usuario=None,
    usuario_nome="",
):
    """
    Grava uma linha na trilha de auditoria.

    - campos: nomes dos campos alterados (não os valores).
    - paciente: informe quando `objeto` já foi apagado ou não é detectável.

    Uma falha ao gravar o log nunca derruba a requisição do usuário.
    """
    try:
        if usuario is None and request is not None:
            usuario = getattr(request, "user", None)
        if usuario is not None and not getattr(usuario, "is_authenticated", False):
            usuario = None

        if paciente is None and objeto is not None:
            paciente = _paciente_de(objeto)

        partes = []
        if campos:
            partes.append("Campos: " + ", ".join(sorted(campos)))
        if detalhes:
            partes.append(detalhes)

        LogAuditoria.objects.create(
            usuario=usuario,
            usuario_nome=(
                (usuario.get_username() if usuario else usuario_nome)
                or ""
            )[:150],
            acao=acao,
            modelo=(modelo or (type(objeto).__name__ if objeto is not None else ""))[:60],
            objeto_id=str(getattr(objeto, "pk", "") or "")[:40],
            objeto_repr=(str(objeto) if objeto is not None else "")[:255],
            paciente=paciente if getattr(paciente, "pk", None) else None,
            detalhes=" | ".join(partes),
            ip=_ip(request),
        )
    except Exception:  # pragma: no cover - o log não pode quebrar o fluxo
        logger.exception("Falha ao registrar auditoria")
