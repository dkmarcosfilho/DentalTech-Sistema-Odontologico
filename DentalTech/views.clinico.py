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
    TratamentoForm,
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
# Tratamentos
# ==========================================================

def _tratamentos_do_paciente(paciente):
    return Tratamento.objects.filter(
        odontograma__paciente=paciente
    ).select_related("dente")


@login_required
def tratamento_list(request, pk):
    paciente = get_paciente_ou_404(request, pk)
    situacao = request.GET.get("situacao", "")
    tratamentos = _tratamentos_do_paciente(paciente)

    if situacao == "andamento":
        tratamentos = tratamentos.filter(concluido=False)
    elif situacao == "concluidos":
        tratamentos = tratamentos.filter(concluido=True)
    else:
        situacao = ""

    pagina, querystring = paginar(request, tratamentos)
    registrar(request, Acao.VISUALIZOU, paciente, modelo="Tratamento",
              detalhes="Lista de tratamentos")

    return render(
        request,
        "DentalTech/tratamentos/list.html",
        {"paciente": paciente, "pagina": pagina,
         "querystring": querystring, "situacao": situacao},
    )


@login_required
def tratamento_create(request, pk):
    paciente = get_paciente_ou_404(request, pk)
    form = TratamentoForm(request.POST or None, paciente=paciente,
                          initial={"data_inicio": timezone.localdate()})

    if form.is_valid():
        tratamento = form.save()
        registrar(request, Acao.CRIOU, tratamento)
        messages.success(request, "Tratamento cadastrado.")
        return redirect("DentalTech:tratamentos", pk=paciente.pk)

    return render(
        request,
        "DentalTech/tratamentos/form.html",
        {"form": form, "paciente": paciente, "titulo": "Novo tratamento"},
    )


@login_required
def tratamento_update(request, pk, tratamento_id):
    paciente = get_paciente_ou_404(request, pk)
    tratamento = get_object_or_404(_tratamentos_do_paciente(paciente), pk=tratamento_id)
    form = TratamentoForm(request.POST or None, instance=tratamento, paciente=paciente)

    if form.is_valid():
        campos = list(form.changed_data)
        form.save()
        registrar(request, Acao.ALTEROU, tratamento, campos=campos)
        messages.success(request, "Tratamento atualizado.")
        return redirect("DentalTech:tratamentos", pk=paciente.pk)

    return render(
        request,
        "DentalTech/tratamentos/form.html",
        {"form": form, "paciente": paciente, "titulo": "Editar tratamento"},
    )


@login_required
@require_POST
def tratamento_concluir(request, pk, tratamento_id):
    paciente = get_paciente_ou_404(request, pk)
    tratamento = get_object_or_404(_tratamentos_do_paciente(paciente), pk=tratamento_id)

    if not tratamento.concluido:
        tratamento.concluido = True
        tratamento.data_conclusao = tratamento.data_conclusao or timezone.localdate()
        tratamento.save(update_fields=["concluido", "data_conclusao"])
        registrar(request, Acao.ALTEROU, tratamento, campos=["concluido"])
        messages.success(request, "Tratamento concluído.")

    return redirect("DentalTech:tratamentos", pk=paciente.pk)


@login_required
def tratamento_delete(request, pk, tratamento_id):
    paciente = get_paciente_ou_404(request, pk)
    tratamento = get_object_or_404(_tratamentos_do_paciente(paciente), pk=tratamento_id)

    if request.method == "POST":
        registrar(request, Acao.EXCLUIU, tratamento)
        tratamento.delete()
        messages.success(request, "Tratamento excluído.")
        return redirect("DentalTech:tratamentos", pk=paciente.pk)

    return render(
        request,
        "DentalTech/confirm_delete.html",
        {
            "titulo": "Excluir tratamento",
            "objeto": tratamento.nome,
            "descricao": f"O tratamento de {paciente.nome} será removido do histórico.",
            "impactos": [],
            "cancel_url": "DentalTech:tratamentos",
            "cancel_pk": paciente.pk,
        },
    )



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
