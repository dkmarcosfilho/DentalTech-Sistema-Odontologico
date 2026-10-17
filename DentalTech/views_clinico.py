"""Telas clínicas: prontuário, odontograma/dentes, tratamentos e procedimentos."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .auditoria import registrar
from .anamnese_perguntas import montar_resumo
from .forms import (
    AnamneseForm,
    ProcedimentoForm,
    TratamentoForm,
    ProntuarioForm,
    OdontogramaObservacoesForm,
    DenteForm
)
from .models import (

    DENTES_DECIDUOS,
    DENTES_PERMANENTES,
    Anamnese,
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
# Prontuário
# ==========================================================

@login_required
def prontuario_detail(request, pk):
    paciente = get_paciente_ou_404(request, pk)
    prontuario = Prontuario.objects.filter(paciente=paciente).first()
    registrar(request, Acao.VISUALIZOU, prontuario or paciente,
              paciente=paciente, modelo="Prontuario")

    return render(
        request,
        "DentalTech/pacientes/prontuario.html",
        {"paciente": paciente, "prontuario": prontuario},
    )


@login_required
def prontuario_update(request, pk):
    paciente = get_paciente_ou_404(request, pk)
    prontuario = Prontuario.objects.filter(paciente=paciente).first()
    novo = prontuario is None
    form = ProntuarioForm(
        request.POST or None,
        instance=prontuario or Prontuario(paciente=paciente),
    )

    if form.is_valid():
        campos = list(form.changed_data)
        prontuario = form.save()
        registrar(request, Acao.CRIOU if novo else Acao.ALTEROU, prontuario,
                  campos=None if novo else campos)
        messages.success(request, "Prontuário salvo.")
        return redirect("DentalTech:prontuario", pk=paciente.pk)

    return render(
        request,
        "DentalTech/pacientes/prontuario_form.html",
        {"form": form, "paciente": paciente},
    )

# ==========================================================
# Anamnese
# ==========================================================

def _anamnese_do(paciente):
    """Cada paciente tem a sua; se por algum motivo faltar, cria em branco."""
    anamnese, _ = Anamnese.objects.get_or_create(paciente=paciente)
    return anamnese


@login_required
def anamnese_detail(request, pk):
    paciente = get_paciente_ou_404(request, pk)
    anamnese = _anamnese_do(paciente)
    registrar(request, Acao.VISUALIZOU, anamnese, paciente=paciente)

    return render(
        request,
        "DentalTech/pacientes/anamnese.html",
        {
            "paciente": paciente,
            "anamnese": anamnese,
            "resumo": montar_resumo(anamnese.respostas),
        },
    )


@login_required
def anamnese_update(request, pk):
    paciente = get_paciente_ou_404(request, pk)
    anamnese = _anamnese_do(paciente)
    form = AnamneseForm(request.POST or None, anamnese=anamnese)

    if request.method == "POST" and form.is_valid():
        campos = list(form.changed_data)
        form.salvar()
        registrar(request, Acao.ALTEROU, anamnese,
                  paciente=paciente, campos=campos)
        messages.success(request, "Anamnese salva.")
        return redirect("DentalTech:anamnese", pk=paciente.pk)

    return render(
        request,
        "DentalTech/pacientes/anamnese_form.html",
        {"form": form, "paciente": paciente, "secoes": form.secoes()},
    )

# ==========================================================
# Odontograma e dentes
# ==========================================================

def _arcadas(dentes, decidua):
    """Monta os 4 quadrantes na ordem visual (da direita do paciente p/ esquerda)."""
    def d(numero):
        dente = dentes.get(numero)
        return {
            "numero": numero,
            "status": dente.status if dente else "SEM_REGISTRO",
            "rotulo": dente.get_status_display() if dente else "Sem registro",
            "obs": bool(dente and dente.observacoes),
        }

    if decidua:
        sup_d, sup_e = range(55, 50, -1), range(61, 66)
        inf_d, inf_e = range(85, 80, -1), range(71, 76)
    else:
        sup_d, sup_e = range(18, 10, -1), range(21, 29)
        inf_d, inf_e = range(48, 40, -1), range(31, 39)

    return {
        "superior": [[d(n) for n in sup_d], [d(n) for n in sup_e]],
        "inferior": [[d(n) for n in inf_d], [d(n) for n in inf_e]],
    }


@login_required
def odontograma_detail(request, pk):
    paciente = get_paciente_ou_404(request, pk)
    odontograma = Odontograma.objects.filter(paciente=paciente).first()
    decidua = request.GET.get("denticao") == "decidua"

    form = OdontogramaObservacoesForm(
        request.POST or None,
        instance=odontograma or Odontograma(paciente=paciente),
    )

    if request.method == "POST" and form.is_valid():
        odontograma = form.save()
        registrar(request, Acao.ALTEROU, odontograma, campos=["observacoes"])
        messages.success(request, "Observações do odontograma salvas.")
        return redirect("DentalTech:odontograma", pk=paciente.pk)

    dentes = {}
    if odontograma:
        dentes = {d.numero: d for d in odontograma.dentes.all()}
    if request.method != "POST":
        registrar(request, Acao.VISUALIZOU, odontograma or paciente,
                  paciente=paciente, modelo="Odontograma")

    return render(
        request,
        "DentalTech/pacientes/odontograma.html",
        {
            "paciente": paciente,
            "arcadas": _arcadas(dentes, decidua),
            "decidua": decidua,
            "status_choices": Dente.Status.choices,
            "form": form,
        },
    )


@login_required
def dente_update(request, pk, numero):
    paciente = get_paciente_ou_404(request, pk)

    if numero not in DENTES_PERMANENTES + DENTES_DECIDUOS:
        return redirect("DentalTech:odontograma", pk=paciente.pk)

    odontograma = Odontograma.objects.filter(paciente=paciente).first()
    dente = None
    if odontograma:
        dente = Dente.objects.filter(odontograma=odontograma, numero=numero).first()

    form = DenteForm(request.POST or None, instance=dente)

    if form.is_valid():
        campos = list(form.changed_data)
        dente = paciente.obter_dente(numero)
        dente.status = form.cleaned_data["status"]
        dente.observacoes = form.cleaned_data["observacoes"]
        dente.save()
        registrar(request, Acao.ALTEROU, dente, campos=campos)
        messages.success(request, f"Dente {numero} atualizado.")
        destino = reverse("DentalTech:odontograma", args=[paciente.pk])
        if numero in DENTES_DECIDUOS:
            destino += "?denticao=decidua"
        return redirect(destino)

    tratamentos = procedimentos = []
    if dente:
        tratamentos = dente.tratamentos.all()
        procedimentos = (
            AtendimentoProcedimento.objects
            .filter(dente=dente)
            .select_related("procedimento", "atendimento__agendamento", "atendimento__profissional")
            .order_by("-atendimento__data")
        )
    else:
        registrar(request, Acao.VISUALIZOU, paciente, modelo="Dente",
                  detalhes=f"Dente {numero}")

    if dente:
        registrar(request, Acao.VISUALIZOU, dente)

    return render(
        request,
        "DentalTech/pacientes/dente_form.html",
        {
            "paciente": paciente,
            "numero": numero,
            "form": form,
            "tratamentos": tratamentos,
            "procedimentos": procedimentos,
        },
    )


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
