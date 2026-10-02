from datetime import date

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import (
    AgendamentoForm,
    CadastroForm,
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


def get_profissional_logado(request):
    """
    Retorna o profissional ligado ao usuário logado.

    Usuários administrativos (staff/superuser) têm acesso geral
    e retornam None.
    """
    if request.user.is_staff or request.user.is_superuser:
        return None

    try:
        return request.user.profissional
    except Profissional.DoesNotExist:
        raise PermissionDenied(
            "Este usuário não está vinculado a um dentista."
        )


def usuario_tem_acesso_geral(request):
    return request.user.is_staff or request.user.is_superuser


@login_required
def dashboard(request):
    hoje = date.today()
    profissional = get_profissional_logado(request)

    proximos = Agendamento.objects.filter(
        data__gte=hoje,
        status__in=[
            Agendamento.Status.AGENDADA,
            Agendamento.Status.CONFIRMADA,
        ],
    ).select_related("paciente", "profissional")

    agendamentos_hoje = Agendamento.objects.filter(data=hoje)

    atendimentos_recentes = Atendimento.objects.select_related(
        "agendamento__paciente",
        "profissional",
    )

    if profissional:
        proximos = proximos.filter(
            profissional=profissional
        )

        agendamentos_hoje = agendamentos_hoje.filter(
            profissional=profissional
        )

        atendimentos_recentes = atendimentos_recentes.filter(
            profissional=profissional
        )

    proximos = proximos[:6]
    atendimentos_recentes = atendimentos_recentes[:5]

    if profissional:
        total_pacientes = Paciente.objects.filter(
            agendamentos__profissional=profissional
        ).distinct().count()
    else:
        total_pacientes = Paciente.objects.count()

    return render(
        request,
        "DentalTech/dashboard.html",
        {
            "total_pacientes": total_pacientes,
            "agendamentos_hoje": agendamentos_hoje.count(),
            "atendimentos_recentes": atendimentos_recentes,
            "proximos_agendamentos": proximos,
            "data_hoje": hoje,
        },
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("DentalTech:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)

            next_url = (
                request.GET.get("next")
                or request.POST.get("next")
            )

            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
            ):
                return redirect(next_url)

            return redirect("DentalTech:dashboard")

        messages.error(
            request,
            "Usuário ou senha inválidos.",
        )

    return render(
        request,
        "DentalTech/login.html",
    )


def cadastro_view(request):
    if request.user.is_authenticated:
        return redirect("DentalTech:dashboard")

    if request.method == "POST":
        form = CadastroForm(request.POST)

        if form.is_valid():
            user = form.save()

            messages.success(
                request,
                f"Usuário {user.username} criado com sucesso! "
                "Faça login para acessar o DentalTech.",
            )

            return redirect("DentalTech:login")
    else:
        form = CadastroForm()

    return render(
        request,
        "DentalTech/cadastro.html",
        {"form": form},
    )


def logout_view(request):
    logout(request)

    messages.success(
        request,
        "Você saiu do DentalTech.",
    )

    return redirect("DentalTech:login")


@login_required
def paciente_list(request):
    profissional = get_profissional_logado(request)
    termo = request.GET.get("q", "").strip()

    if profissional:
        pacientes = Paciente.objects.filter(
            agendamentos__profissional=profissional
        ).distinct()
    else:
        pacientes = Paciente.objects.all()

    if termo:
        pacientes = pacientes.filter(
            Q(nome__icontains=termo)
            | Q(cpf__icontains=termo)
            | Q(email__icontains=termo)
            | Q(telefone__icontains=termo)
        )

    pacientes = pacientes.order_by("nome")

    return render(
        request,
        "DentalTech/pacientes/list.html",
        {
            "pacientes": pacientes,
            "termo": termo,
        },
    )


@login_required
def paciente_detail(request, pk):
    profissional = get_profissional_logado(request)

    if profissional:
        paciente = get_object_or_404(
            Paciente.objects.prefetch_related(
                "agendamentos__profissional"
            ),
            pk=pk,
            agendamentos__profissional=profissional,
        )

        agendamentos = paciente.agendamentos.filter(
            profissional=profissional
        ).select_related("profissional")

    else:
        paciente = get_object_or_404(
            Paciente.objects.prefetch_related(
                "agendamentos__profissional"
            ),
            pk=pk,
        )

        agendamentos = paciente.agendamentos.select_related(
            "profissional"
        )

    return render(
        request,
        "DentalTech/pacientes/detail.html",
        {
            "paciente": paciente,
            "agendamentos": agendamentos,
        },
    )


@login_required
def paciente_create(request):
    form = PacienteForm(request.POST or None)

    if form.is_valid():
        paciente = form.save()

        messages.success(
            request,
            "Paciente cadastrado com sucesso. "
            "Agora crie um agendamento para vinculá-lo ao dentista.",
        )

        return redirect(
            "DentalTech:paciente_detail",
            pk=paciente.pk,
        )

    return render(
        request,
        "DentalTech/pacientes/form.html",
        {
            "form": form,
            "titulo": "Novo paciente",
        },
    )


@login_required
def paciente_update(request, pk):
    profissional = get_profissional_logado(request)

    if profissional:
        paciente = get_object_or_404(
            Paciente,
            pk=pk,
            agendamentos__profissional=profissional,
        )
    else:
        paciente = get_object_or_404(
            Paciente,
            pk=pk,
        )

    form = PacienteForm(
        request.POST or None,
        instance=paciente,
    )

    if form.is_valid():
        form.save()

        messages.success(
            request,
            "Dados do paciente atualizados.",
        )

        return redirect(
            "DentalTech:paciente_detail",
            pk=paciente.pk,
        )

    return render(
        request,
        "DentalTech/pacientes/form.html",
        {
            "form": form,
            "titulo": "Editar paciente",
        },
    )


@login_required
def agendamento_list(request):
    profissional_logado = get_profissional_logado(request)

    agendamentos = Agendamento.objects.select_related(
        "paciente",
        "profissional",
    )

    if profissional_logado:
        agendamentos = agendamentos.filter(
            profissional=profissional_logado
        )

    data = request.GET.get("data", "")
    status = request.GET.get("status", "")
    profissional_filtro = request.GET.get(
        "profissional",
        "",
    )

    if data:
        agendamentos = agendamentos.filter(
            data=data
        )

    if status:
        agendamentos = agendamentos.filter(
            status=status
        )

    if profissional_logado:
        profissional_filtro = str(
            profissional_logado.pk
        )

    elif profissional_filtro:
        agendamentos = agendamentos.filter(
            profissional_id=profissional_filtro
        )

    if profissional_logado:
        profissionais = Profissional.objects.filter(
            pk=profissional_logado.pk
        )
    else:
        profissionais = Profissional.objects.all()

    return render(
        request,
        "DentalTech/agenda/list.html",
        {
            "agendamentos": agendamentos,
            "profissionais": profissionais,
            "status_choices": Agendamento.Status.choices,
            "filtros": {
                "data": data,
                "status": status,
                "profissional": profissional_filtro,
            },
            "acesso_geral": usuario_tem_acesso_geral(
                request
            ),
        },
    )


@login_required
def agendamento_create(request):
    profissional_logado = get_profissional_logado(request)

    if (
        profissional_logado is None
        and not usuario_tem_acesso_geral(request)
    ):
        raise PermissionDenied

    form = AgendamentoForm(
        request.POST or None
    )

    if form.is_valid():
        agendamento = form.save(commit=False)

        if profissional_logado:
            agendamento.profissional = profissional_logado

        else:
            profissional_id = request.POST.get(
                "profissional"
            )

            if not profissional_id:
                form.add_error(
                    None,
                    "Selecione o dentista responsável "
                    "pelo agendamento.",
                )

                return render(
                    request,
                    "DentalTech/agenda/form.html",
                    {
                        "form": form,
                        "titulo": "Novo agendamento",
                        "acesso_geral": True,
                    },
                )

            agendamento.profissional_id = profissional_id

        agendamento.save()

        messages.success(
            request,
            "Agendamento criado com sucesso.",
        )

        return redirect(
            "DentalTech:agenda"
        )

    if usuario_tem_acesso_geral(request):
        profissionais = Profissional.objects.order_by(
            "nome"
        )
    else:
        profissionais = None

    return render(
        request,
        "DentalTech/agenda/form.html",
        {
            "form": form,
            "titulo": "Novo agendamento",
            "profissionais": profissionais,
            "acesso_geral": usuario_tem_acesso_geral(
                request
            ),
        },
    )


@login_required
def agendamento_update(request, pk):
    profissional_logado = get_profissional_logado(
        request
    )

    if profissional_logado:
        agendamento = get_object_or_404(
            Agendamento,
            pk=pk,
            profissional=profissional_logado,
        )
    else:
        agendamento = get_object_or_404(
            Agendamento,
            pk=pk,
        )

    form = AgendamentoForm(
        request.POST or None,
        instance=agendamento,
    )

    if form.is_valid():
        agendamento_atualizado = form.save(
            commit=False
        )

        if profissional_logado:
            agendamento_atualizado.profissional = (
                profissional_logado
            )

        agendamento_atualizado.save()

        messages.success(
            request,
            "Agendamento atualizado.",
        )

        return redirect(
            "DentalTech:agenda"
        )

    profissionais = (
        Profissional.objects.order_by("nome")
        if usuario_tem_acesso_geral(request)
        else None
    )

    return render(
        request,
        "DentalTech/agenda/form.html",
        {
            "form": form,
            "titulo": "Editar agendamento",
            "agendamento": agendamento,
            "profissionais": profissionais,
            "acesso_geral": usuario_tem_acesso_geral(
                request
            ),
        },
    )


@login_required
def dentistas(request):
    profissionais = Profissional.objects.select_related(
        "usuario"
    ).all()

    return render(
        request,
        "DentalTech/dentistas/list.html",
        {
            "profissionais": profissionais,
        },
    )


@login_required
def dentista_create(request):
    if not usuario_tem_acesso_geral(request):
        raise PermissionDenied(
            "Somente administradores podem cadastrar dentistas."
        )

    form = ProfissionalForm(
        request.POST or None
    )

    if form.is_valid():
        form.save()

        messages.success(
            request,
            "Dentista cadastrado com sucesso.",
        )

        return redirect(
            "DentalTech:dentistas"
        )

    return render(
        request,
        "DentalTech/dentistas/form.html",
        {
            "form": form,
            "titulo": "Novo dentista",
        },
    )


@login_required
def dentista_update(request, pk):
    if not usuario_tem_acesso_geral(request):
        raise PermissionDenied(
            "Somente administradores podem editar dentistas."
        )

    profissional = get_object_or_404(
        Profissional,
        pk=pk,
    )

    form = ProfissionalForm(
        request.POST or None,
        instance=profissional,
    )

    if form.is_valid():
        form.save()

        messages.success(
            request,
            "Dentista atualizado com sucesso.",
        )

        return redirect(
            "DentalTech:dentistas"
        )

    return render(
        request,
        "DentalTech/dentistas/form.html",
        {
            "form": form,
            "titulo": "Editar dentista",
        },
    )


@login_required
def relatorios(request):
    profissional = get_profissional_logado(
        request
    )

    if profissional:
        relatorios = Relatorio.objects.filter(
            gerado_por=request.user
        ).select_related("gerado_por")

        total_pacientes = Paciente.objects.filter(
            agendamentos__profissional=profissional
        ).distinct().count()

        total_dentistas = 1

        total_agendamentos = Agendamento.objects.filter(
            profissional=profissional
        ).count()

        total_atendimentos = Atendimento.objects.filter(
            profissional=profissional
        ).count()

        agendamentos_pendentes = Agendamento.objects.filter(
            profissional=profissional,
            status__in=[
                Agendamento.Status.AGENDADA,
                Agendamento.Status.CONFIRMADA,
            ],
        ).count()

    else:
        relatorios = Relatorio.objects.select_related(
            "gerado_por"
        ).all()

        total_pacientes = Paciente.objects.count()
        total_dentistas = Profissional.objects.count()
        total_agendamentos = Agendamento.objects.count()
        total_atendimentos = Atendimento.objects.count()

        agendamentos_pendentes = Agendamento.objects.filter(
            status__in=[
                Agendamento.Status.AGENDADA,
                Agendamento.Status.CONFIRMADA,
            ],
        ).count()

    contexto = {
        "relatorios": relatorios,
        "total_pacientes": total_pacientes,
        "total_dentistas": total_dentistas,
        "total_agendamentos": total_agendamentos,
        "total_atendimentos": total_atendimentos,
        "agendamentos_pendentes": agendamentos_pendentes,
    }

    return render(
        request,
        "DentalTech/relatorios.html",
        contexto,
    )


@login_required
def configuracoes(request):
    return render(
        request,
        "DentalTech/configuracoes.html",
        {
            "usuario": request.user,
            "dentistas": Profissional.objects.count(),
        },
    )


@login_required
def atendimento_create(request, agendamento_id):
    profissional_logado = get_profissional_logado(
        request
    )

    if profissional_logado:
        agendamento = get_object_or_404(
            Agendamento.objects.select_related(
                "paciente",
                "profissional",
            ),
            pk=agendamento_id,
            profissional=profissional_logado,
        )

    else:
        agendamento = get_object_or_404(
            Agendamento.objects.select_related(
                "paciente",
                "profissional",
            ),
            pk=agendamento_id,
        )

    atendimento = getattr(
        agendamento,
        "atendimento",
        None,
    )

    if atendimento:
        return redirect(
            "DentalTech:atendimento_detail",
            pk=atendimento.pk,
        )

    form = AtendimentoForm(
        request.POST or None
    )

    if form.is_valid():
        atendimento = form.save(
            commit=False
        )

        atendimento.agendamento = agendamento
        atendimento.profissional = (
            agendamento.profissional
        )

        atendimento.save()

        messages.success(
            request,
            "Atendimento registrado.",
        )

        return redirect(
            "DentalTech:atendimento_detail",
            pk=atendimento.pk,
        )

    return render(
        request,
        "DentalTech/atendimentos/form.html",
        {
            "form": form,
            "agendamento": agendamento,
            "titulo": "Registrar atendimento",
        },
    )


@login_required
def atendimento_detail(request, pk):
    profissional_logado = get_profissional_logado(
        request
    )

    queryset = Atendimento.objects.select_related(
        "agendamento__paciente",
        "agendamento__profissional",
        "profissional",
    ).prefetch_related(
        "procedimentos__procedimento",
        "procedimentos__dente",
    )

    if profissional_logado:
        atendimento = get_object_or_404(
            queryset,
            pk=pk,
            profissional=profissional_logado,
        )

    else:
        atendimento = get_object_or_404(
            queryset,
            pk=pk,
        )

    return render(
        request,
        "DentalTech/atendimentos/detail.html",
        {
            "atendimento": atendimento,
        },
    )


@login_required
def atendimento_update(request, pk):
    profissional_logado = get_profissional_logado(
        request
    )

    if profissional_logado:
        atendimento = get_object_or_404(
            Atendimento,
            pk=pk,
            profissional=profissional_logado,
        )

    else:
        atendimento = get_object_or_404(
            Atendimento,
            pk=pk,
        )

    form = AtendimentoForm(
        request.POST or None,
        instance=atendimento,
    )

    formset = AtendimentoProcedimentoFormSet(
        request.POST or None,
        instance=atendimento,
    )

    if form.is_valid() and formset.is_valid():
        atendimento_atualizado = form.save(
            commit=False
        )

        atendimento_atualizado.profissional = (
            atendimento.agendamento.profissional
        )

        atendimento_atualizado.save()

        formset.instance = atendimento_atualizado
        formset.save()

        messages.success(
            request,
            "Atendimento atualizado.",
        )

        return redirect(
            "DentalTech:atendimento_detail",
            pk=pk,
        )

    return render(
        request,
        "DentalTech/atendimentos/form.html",
        {
            "form": form,
            "formset": formset,
            "agendamento": atendimento.agendamento,
            "atendimento": atendimento,
            "titulo": "Editar atendimento",
        },
    )