from datetime import date

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import (
    AgendamentoForm,
    AtendimentoForm,
    AtendimentoProcedimentoFormSet,
    PacienteForm,
    ProfissionalForm,
)
from .models import (
    Agendamento,
    Atendimento,
    Paciente,
    Profissional,
    Relatorio,
)


@login_required
def dashboard(request):
    hoje = date.today()
    proximos = Agendamento.objects.filter(
        data__gte=hoje,
        status__in=[Agendamento.Status.AGENDADA, Agendamento.Status.CONFIRMADA],
    ).select_related("paciente", "profissional")[:6]
    return render(request, "DentalTech/dashboard.html", {
        "total_pacientes": Paciente.objects.count(),
        "agendamentos_hoje": Agendamento.objects.filter(data=hoje).count(),
        "atendimentos_recentes": Atendimento.objects.select_related(
            "agendamento__paciente", "profissional"
        )[:5],
        "proximos_agendamentos": proximos,
        "data_hoje": hoje,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect("DentalTech:dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect("DentalTech:dashboard")
        messages.error(request, "Usuário ou senha inválidos.")
    return render(request, "DentalTech/login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "Você saiu do DentalTech.")
    return redirect("DentalTech:login")


@login_required
def paciente_list(request):
    termo = request.GET.get("q", "").strip()
    pacientes = Paciente.objects.all()
    if termo:
        pacientes = pacientes.filter(
            Q(nome__icontains=termo) | Q(cpf__icontains=termo) |
            Q(email__icontains=termo) | Q(telefone__icontains=termo)
        )
    return render(request, "DentalTech/pacientes/list.html", {"pacientes": pacientes, "termo": termo})


@login_required
def paciente_detail(request, pk):
    paciente = get_object_or_404(
        Paciente.objects.prefetch_related("agendamentos__profissional"),
        pk=pk,
    )
    return render(request, "DentalTech/pacientes/detail.html", {"paciente": paciente})


@login_required
def paciente_create(request):
    form = PacienteForm(request.POST or None)
    if form.is_valid():
        paciente = form.save()
        messages.success(request, "Paciente cadastrado com sucesso.")
        return redirect("DentalTech:paciente_detail", pk=paciente.pk)
    return render(request, "DentalTech/pacientes/form.html", {"form": form, "titulo": "Novo paciente"})


@login_required
def paciente_update(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    form = PacienteForm(request.POST or None, instance=paciente)
    if form.is_valid():
        form.save()
        messages.success(request, "Dados do paciente atualizados.")
        return redirect("DentalTech:paciente_detail", pk=paciente.pk)
    return render(request, "DentalTech/pacientes/form.html", {"form": form, "titulo": "Editar paciente"})


@login_required
def agendamento_list(request):
    agendamentos = Agendamento.objects.select_related("paciente", "profissional")
    data = request.GET.get("data", "")
    status = request.GET.get("status", "")
    profissional = request.GET.get("profissional", "")
    if data:
        agendamentos = agendamentos.filter(data=data)
    if status:
        agendamentos = agendamentos.filter(status=status)
    if profissional:
        agendamentos = agendamentos.filter(profissional_id=profissional)
    return render(request, "DentalTech/agenda/list.html", {
        "agendamentos": agendamentos,
        "profissionais": Profissional.objects.all(),
        "status_choices": Agendamento.Status.choices,
        "filtros": {"data": data, "status": status, "profissional": profissional},
    })


@login_required
def agendamento_create(request):
    form = AgendamentoForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Agendamento criado com sucesso.")
        return redirect("DentalTech:agenda")
    return render(request, "DentalTech/agenda/form.html", {"form": form, "titulo": "Novo agendamento"})


@login_required
def agendamento_update(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    form = AgendamentoForm(request.POST or None, instance=agendamento)
    if form.is_valid():
        form.save()
        messages.success(request, "Agendamento atualizado.")
        return redirect("DentalTech:agenda")
    return render(request, "DentalTech/agenda/form.html", {"form": form, "titulo": "Editar agendamento"})


@login_required
def dentistas(request):
    profissionais = Profissional.objects.select_related("usuario").all()
    return render(request, "DentalTech/dentistas/list.html", {"profissionais": profissionais})


@login_required
def dentista_create(request):
    form = ProfissionalForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Dentista cadastrado com sucesso.")
        return redirect("DentalTech:dentistas")
    return render(request, "DentalTech/dentistas/form.html", {
        "form": form, "titulo": "Novo dentista"
    })


@login_required
def dentista_update(request, pk):
    profissional = get_object_or_404(Profissional, pk=pk)
    form = ProfissionalForm(request.POST or None, instance=profissional)
    if form.is_valid():
        form.save()
        messages.success(request, "Dentista atualizado com sucesso.")
        return redirect("DentalTech:dentistas")
    return render(request, "DentalTech/dentistas/form.html", {
        "form": form, "titulo": "Editar dentista"
    })


@login_required
def relatorios(request):
    relatorios = Relatorio.objects.select_related("gerado_por").all()
    contexto = {
        "relatorios": relatorios,
        "total_pacientes": Paciente.objects.count(),
        "total_dentistas": Profissional.objects.count(),
        "total_agendamentos": Agendamento.objects.count(),
        "total_atendimentos": Atendimento.objects.count(),
        "agendamentos_pendentes": Agendamento.objects.filter(
            status__in=[Agendamento.Status.AGENDADA, Agendamento.Status.CONFIRMADA]
        ).count(),
    }
    return render(request, "DentalTech/relatorios.html", contexto)


@login_required
def configuracoes(request):
    return render(request, "DentalTech/configuracoes.html", {
        "usuario": request.user,
        "dentistas": Profissional.objects.count(),
    })


@login_required
def atendimento_create(request, agendamento_id):
    agendamento = get_object_or_404(
        Agendamento.objects.select_related("paciente", "profissional"), pk=agendamento_id
    )
    atendimento = getattr(agendamento, "atendimento", None)
    if atendimento:
        return redirect("DentalTech:atendimento_detail", pk=atendimento.pk)
    form = AtendimentoForm(request.POST or None, initial={"profissional": agendamento.profissional})
    if form.is_valid():
        atendimento = form.save(commit=False)
        atendimento.agendamento = agendamento
        atendimento.save()
        messages.success(request, "Atendimento registrado.")
        return redirect("DentalTech:atendimento_detail", pk=atendimento.pk)
    return render(request, "DentalTech/atendimentos/form.html", {
        "form": form, "agendamento": agendamento, "titulo": "Registrar atendimento",
    })


@login_required
def atendimento_detail(request, pk):
    atendimento = get_object_or_404(
        Atendimento.objects.select_related(
            "agendamento__paciente", "agendamento__profissional", "profissional"
        ).prefetch_related("procedimentos__procedimento", "procedimentos__dente"),
        pk=pk,
    )
    return render(request, "DentalTech/atendimentos/detail.html", {"atendimento": atendimento})


@login_required
def atendimento_update(request, pk):
    atendimento = get_object_or_404(Atendimento, pk=pk)
    form = AtendimentoForm(request.POST or None, instance=atendimento)
    formset = AtendimentoProcedimentoFormSet(request.POST or None, instance=atendimento)
    if form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        messages.success(request, "Atendimento atualizado.")
        return redirect("DentalTech:atendimento_detail", pk=pk)
    return render(request, "DentalTech/atendimentos/form.html", {
        "form": form, "formset": formset, "agendamento": atendimento.agendamento,
        "atendimento": atendimento, "titulo": "Editar atendimento",
    })
