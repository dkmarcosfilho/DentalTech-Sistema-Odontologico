"""Telas clínicas: prontuário, odontograma/dentes, tratamentos e procedimentos."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .auditoria import registrar
from .forms import (
    ProcedimentoForm,
)
from .models import (
    DENTES_DECIDUOS,
    DENTES_PERMANENTES,
    AtendimentoProcedimento,
    Dente,
    LogAuditoria,
    Odontograma,
    Procedimento,
    Prontuario,
    Tratamento,
)
from .permissoes import admin_required, get_paciente_ou_404, usuario_tem_acesso_geral
from .utils import paginar

Acao = LogAuditoria.Acao


# ==========================================================
# Procedimentos (cadastro e preços)
# ==========================================================

@login_required
def procedimento_list(request):
    termo = request.GET.get("q", "").strip()
    situacao = request.GET.get("situacao", "")
    procedimentos = Procedimento.objects.all()

    if termo:
        procedimentos = procedimentos.filter(
            Q(nome__icontains=termo) | Q(descricao__icontains=termo)
        )
    if situacao == "ativos":
        procedimentos = procedimentos.filter(ativo=True)
    elif situacao == "inativos":
        procedimentos = procedimentos.filter(ativo=False)
    else:
        situacao = ""

    pagina, querystring = paginar(request, procedimentos)

    return render(
        request,
        "DentalTech/procedimentos/list.html",
        {
            "pagina": pagina,
            "querystring": querystring,
            "termo": termo,
            "situacao": situacao,
            "acesso_geral": usuario_tem_acesso_geral(request),
        },
    )


@admin_required
def procedimento_create(request):
    form = ProcedimentoForm(request.POST or None, initial={"ativo": True})

    if form.is_valid():
        procedimento = form.save()
        registrar(request, Acao.CRIOU, procedimento)
        messages.success(request, "Procedimento cadastrado.")
        return redirect("DentalTech:procedimentos")

    return render(
        request,
        "DentalTech/procedimentos/form.html",
        {"form": form, "titulo": "Novo procedimento"},
    )


@admin_required
def procedimento_update(request, pk):
    procedimento = get_object_or_404(Procedimento, pk=pk)
    form = ProcedimentoForm(request.POST or None, instance=procedimento)

    if form.is_valid():
        campos = list(form.changed_data)
        form.save()
        registrar(request, Acao.ALTEROU, procedimento, campos=campos)
        messages.success(
            request,
            "Procedimento atualizado. Atendimentos antigos mantêm o valor "
            "cobrado na época.",
        )
        return redirect("DentalTech:procedimentos")

    return render(
        request,
        "DentalTech/procedimentos/form.html",
        {"form": form, "titulo": "Editar procedimento"},
    )
