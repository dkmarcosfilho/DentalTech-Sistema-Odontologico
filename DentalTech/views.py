from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .auditoria import registrar
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
    LogAuditoria,
    Paciente,
    Profissional,
    Relatorio,
)

from .permissoes import (  # noqa: F401  (reexportados para compatibilidade)
    admin_required,
    agendamentos_visiveis,
    get_paciente_ou_404,
    get_profissional_logado,
    pacientes_visiveis,
    usuario_tem_acesso_geral,
)
from .utils import paginar, so_digitos

Acao = LogAuditoria.Acao


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


# ==========================================================
# Pacientes
# ==========================================================

@login_required
def paciente_list(request):
    termo = request.GET.get("q", "").strip()
    pacientes = pacientes_visiveis(request)

    if termo:
        filtro = (
            Q(nome__icontains=termo)
            | Q(email__icontains=termo)
            | Q(telefone__icontains=termo)
        )
        digitos = so_digitos(termo)
        if digitos:
            # "529.982" e "529982" encontram o mesmo CPF.
            filtro |= Q(cpf__icontains=digitos)
        pacientes = pacientes.filter(filtro)

    acesso_geral = usuario_tem_acesso_geral(request)
    pacientes = pacientes.order_by("nome")
    if acesso_geral:
        pacientes = pacientes.prefetch_related("profissionais")

    pagina, querystring = paginar(request, pacientes)

    return render(
        request,
        "DentalTech/pacientes/list.html",
        {
            "pagina": pagina,
            "querystring": querystring,
            "termo": termo,
            "acesso_geral": acesso_geral,
        },
    )


@login_required
def paciente_detail(request, pk):
    profissional = get_profissional_logado(request)
    paciente = get_paciente_ou_404(request, pk)

    agendamentos = paciente.agendamentos.select_related("profissional")
    if profissional:
        agendamentos = agendamentos.filter(profissional=profissional)

    registrar(request, Acao.VISUALIZOU, paciente)

    return render(
        request,
        "DentalTech/pacientes/detail.html",
        {
            "paciente": paciente,
            "agendamentos": agendamentos[:30],
            "profissionais": paciente.profissionais.all(),
            "acesso_geral": usuario_tem_acesso_geral(request),
        },
    )


@login_required
def paciente_create(request):
    profissional = get_profissional_logado(request)
    form = PacienteForm(request.POST or None, acesso_geral=profissional is None)

    if form.is_valid():
        with transaction.atomic():
            paciente = form.save()
            if profissional:
                paciente.profissionais.add(profissional)

        registrar(request, Acao.CRIOU, paciente)
        messages.success(request, "Paciente cadastrado com sucesso.")
        return redirect("DentalTech:paciente_detail", pk=paciente.pk)

    return render(
        request,
        "DentalTech/pacientes/form.html",
        {"form": form, "titulo": "Novo paciente"},
    )


@login_required
def paciente_update(request, pk):
    profissional = get_profissional_logado(request)
    paciente = get_paciente_ou_404(request, pk)

    form = PacienteForm(
        request.POST or None,
        instance=paciente,
        acesso_geral=profissional is None,
    )

    if form.is_valid():
        campos = list(form.changed_data)
        form.save()
        registrar(request, Acao.ALTEROU, paciente, campos=campos)
        messages.success(request, "Dados do paciente atualizados.")
        return redirect("DentalTech:paciente_detail", pk=paciente.pk)

    return render(
        request,
        "DentalTech/pacientes/form.html",
        {"form": form, "titulo": "Editar paciente"},
    )


@login_required
def paciente_delete(request, pk):
    """Exclui um paciente após confirmar os impactos no histórico."""
    profissional = get_profissional_logado(request)
    paciente = get_paciente_ou_404(request, pk)

    # Um dentista não pode apagar um paciente atendido também por colegas.
    if profissional and paciente.profissionais.exclude(pk=profissional.pk).exists():
        messages.error(
            request,
            "Este paciente também é atendido por outros dentistas. "
            "Somente um administrador pode excluí-lo.",
        )
        return redirect("DentalTech:paciente_detail", pk=paciente.pk)

    agendamentos = paciente.agendamentos.all()
    atendimentos = Atendimento.objects.filter(agendamento__paciente=paciente)

    impactos = []
    if agendamentos.count():
        impactos.append(f"{agendamentos.count()} agendamento(s)")
    if atendimentos.count():
        impactos.append(f"{atendimentos.count()} atendimento(s) registrado(s)")
    if hasattr(paciente, "prontuario"):
        impactos.append("prontuário")
    if hasattr(paciente, "odontograma"):
        impactos.append("odontograma e tratamentos")

    if request.method == "POST":
        if impactos and not request.POST.get("confirmar_historico"):
            messages.error(
                request,
                "Marque a confirmação para excluir o paciente junto com o histórico.",
            )
        else:
            nome = paciente.nome
            try:
                with transaction.atomic():
                    # Registra antes: depois o paciente deixa de existir.
                    registrar(
                        request, Acao.EXCLUIU, paciente,
                        detalhes="Exclusão com histórico: " + (", ".join(impactos) or "sem histórico"),
                    )
                    # Atendimento protege o agendamento (PROTECT), por isso
                    # o histórico de atendimento é removido primeiro.
                    atendimentos.delete()
                    paciente.delete()
            except ProtectedError:
                messages.error(
                    request,
                    "Não foi possível excluir este paciente porque existem "
                    "registros relacionados que precisam ser tratados primeiro.",
                )
            else:
                messages.success(request, f"Paciente {nome} excluído.")
                return redirect("DentalTech:pacientes")

    return render(
        request,
        "DentalTech/confirm_delete.html",
        {
            "titulo": "Excluir paciente",
            "objeto": paciente.nome,
            "descricao": "Os dados cadastrais do paciente serão removidos.",
            "impactos": impactos,
            "cancel_url": "DentalTech:paciente_detail",
            "cancel_pk": paciente.pk,
        },
    )

# ==========================================================
# Agenda
# ==========================================================

def _destino(request, padrao="DentalTech:agenda"):
    """Destino pós-ação vindo do formulário, só se for um endereço do próprio site."""
    proximo = request.POST.get("next", "")
    if proximo and url_has_allowed_host_and_scheme(
        proximo,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return proximo
    return padrao


PERIODOS = [
    ("proximos", "Próximos"),
    ("hoje", "Hoje"),
    ("passados", "Passados"),
    ("todos", "Todos"),
]


@login_required
def agendamento_list(request):
    profissional_logado = get_profissional_logado(request)
    agendamentos = agendamentos_visiveis(request).select_related("atendimento")
    hoje = timezone.localdate()

    data_txt = request.GET.get("data", "")
    status = request.GET.get("status", "")
    profissional_filtro = request.GET.get("profissional", "")
    termo = request.GET.get("q", "").strip()
    periodo = request.GET.get("periodo", "proximos")
    if periodo not in dict(PERIODOS):
        periodo = "proximos"

    data = parse_date(data_txt) if data_txt else None

    if data:
        agendamentos = agendamentos.filter(data=data)
    elif periodo == "proximos":
        agendamentos = agendamentos.filter(data__gte=hoje)
    elif periodo == "hoje":
        agendamentos = agendamentos.filter(data=hoje)
    elif periodo == "passados":
        agendamentos = agendamentos.filter(data__lt=hoje).order_by("-data", "-horario")

    if status in dict(Agendamento.Status.choices):
        agendamentos = agendamentos.filter(status=status)
    else:
        status = ""

    if termo:
        agendamentos = agendamentos.filter(paciente__nome__icontains=termo)

    if profissional_logado:
        profissional_filtro = str(profissional_logado.pk)
        profissionais = Profissional.objects.filter(pk=profissional_logado.pk)
    else:
        profissionais = Profissional.objects.all()
        if profissional_filtro.isdigit():
            agendamentos = agendamentos.filter(profissional_id=int(profissional_filtro))
        else:
            profissional_filtro = ""

    pagina, querystring = paginar(request, agendamentos)

    return render(
        request,
        "DentalTech/agenda/list.html",
        {
            "pagina": pagina,
            "querystring": querystring,
            "profissionais": profissionais,
            "status_choices": Agendamento.Status.choices,
            "periodos": PERIODOS,
            "filtros": {
                "data": data_txt if data else "",
                "status": status,
                "profissional": profissional_filtro,
                "q": termo,
                "periodo": periodo,
            },
            "acesso_geral": usuario_tem_acesso_geral(request),
        },
    )


def _salvar_agendamento(request, form, profissional_logado, novo):
    """Salva o agendamento; devolve True se deu certo."""
    agendamento = form.save(commit=False)
    campos = list(form.changed_data)

    if profissional_logado:
        agendamento.profissional = profissional_logado

    try:
        with transaction.atomic():
            agendamento.save()
            # Quando o admin agenda, o paciente passa a ser do dentista
            # (vínculo explícito, avisado na mensagem abaixo).
            vinculado = False
            if not agendamento.paciente.profissionais.filter(
                pk=agendamento.profissional_id
            ).exists():
                agendamento.paciente.profissionais.add(agendamento.profissional)
                vinculado = True
    except IntegrityError:
        # Outra pessoa pegou o horário no mesmo instante.
        form.add_error(None, "Este horário acabou de ser ocupado. Escolha outro.")
        return False

    registrar(
        request,
        Acao.CRIOU if novo else Acao.ALTEROU,
        agendamento,
        campos=None if novo else campos,
    )
    if vinculado:
        registrar(
            request, Acao.ALTEROU, agendamento.paciente,
            campos=["profissionais"],
            detalhes=f"Vinculado a {agendamento.profissional.nome} ao agendar",
        )
        messages.info(
            request,
            f"{agendamento.paciente.nome} foi vinculado(a) a "
            f"{agendamento.profissional.nome}.",
        )
    messages.success(
        request,
        "Agendamento criado com sucesso." if novo else "Agendamento atualizado.",
    )
    return True


@login_required
def agendamento_create(request):
    profissional_logado = get_profissional_logado(request)
    inicial = {}
    paciente_id = request.GET.get("paciente", "")
    if paciente_id.isdigit():
        inicial["paciente"] = int(paciente_id)

    form = AgendamentoForm(
        request.POST or None,
        profissional=profissional_logado,
        initial=inicial,
    )

    if form.is_valid() and _salvar_agendamento(request, form, profissional_logado, True):
        return redirect("DentalTech:agenda")

    return render(
        request,
        "DentalTech/agenda/form.html",
        {"form": form, "titulo": "Novo agendamento"},
    )


@login_required
def agendamento_update(request, pk):
    profissional_logado = get_profissional_logado(request)
    agendamento = get_object_or_404(agendamentos_visiveis(request), pk=pk)

    form = AgendamentoForm(
        request.POST or None,
        instance=agendamento,
        profissional=profissional_logado,
    )

    if form.is_valid() and _salvar_agendamento(request, form, profissional_logado, False):
        return redirect("DentalTech:agenda")

    return render(
        request,
        "DentalTech/agenda/form.html",
        {"form": form, "titulo": "Editar agendamento", "agendamento": agendamento},
    )


@login_required
@require_POST
def agendamento_status(request, pk, novo_status):
    """Confirma ou cancela um agendamento com um clique."""
    Status = Agendamento.Status
    if novo_status not in (Status.CONFIRMADA, Status.CANCELADA):
        raise Http404

    agendamento = get_object_or_404(agendamentos_visiveis(request), pk=pk)
    anterior = agendamento.status

    if anterior in (Status.REALIZADA, Status.CANCELADA, Status.REMARCADA) or (
        novo_status == Status.CONFIRMADA and anterior != Status.AGENDADA
    ):
        messages.error(
            request,
            f"Um agendamento {agendamento.get_status_display().lower()} "
            "não pode mudar para este status.",
        )
    else:
        agendamento.status = novo_status
        agendamento.save(update_fields=["status", "atualizado_em"])
        registrar(
            request, Acao.ALTEROU, agendamento,
            campos=["status"], detalhes=f"{anterior} → {novo_status}",
        )
        messages.success(
            request,
            "Agendamento cancelado." if novo_status == Status.CANCELADA
            else "Agendamento confirmado.",
        )

    return redirect(_destino(request))


@login_required
@require_POST
def agendamento_delete(request, pk):
    agendamento = get_object_or_404(agendamentos_visiveis(request), pk=pk)

    if Atendimento.objects.filter(agendamento=agendamento).exists():
        messages.error(
            request,
            "Este agendamento já tem atendimento registrado e não pode ser "
            "excluído.",
        )
        return redirect("DentalTech:agenda")

    registrar(request, Acao.EXCLUIU, agendamento)
    agendamento.delete()
    messages.success(request, "Agendamento excluído.")
    return redirect(_destino(request))


#DENTISTA

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
            "acesso_geral": usuario_tem_acesso_geral(request),
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
def dentista_delete(request, pk):
    if not usuario_tem_acesso_geral(request):
        raise PermissionDenied(
            "Somente administradores podem excluir dentistas."
        )

    profissional = get_object_or_404(
        Profissional.objects.select_related("usuario"),
        pk=pk,
    )

    agendamentos = profissional.agendamentos.all()
    atendimentos = Atendimento.objects.filter(
        Q(profissional=profissional)
        | Q(agendamento__profissional=profissional)
    )
    usuario = profissional.usuario
    remove_usuario = bool(
        usuario and not (usuario.is_staff or usuario.is_superuser)
    )

    total_agendamentos = agendamentos.count()
    total_atendimentos = atendimentos.count()
    impactos = []

    if total_agendamentos:
        impactos.append(f"{total_agendamentos} agendamento(s)")
    if total_atendimentos:
        impactos.append(f"{total_atendimentos} atendimento(s) registrado(s)")

    if request.method == "POST":
        if impactos and not request.POST.get("confirmar_historico"):
            messages.error(
                request,
                "Marque a confirmação para excluir o dentista "
                "junto com o histórico.",
            )
        else:
            nome = profissional.nome
            with transaction.atomic():
                atendimentos.delete()
                agendamentos.delete()
                profissional.delete()

                if remove_usuario:
                    try:
                        usuario.delete()
                    except ProtectedError:
                        # Usuário tem relatórios gerados: não apaga,
                        # só impede o acesso.
                        usuario.is_active = False
                        usuario.save(update_fields=["is_active"])

            messages.success(request, f"Dentista {nome} excluído.")
            return redirect("DentalTech:dentistas")

    descricao = "O cadastro do dentista será removido."
    if remove_usuario:
        descricao += (
            f" O login \"{usuario.get_username()}\" vinculado a ele "
            "também será removido."
        )

    return render(
        request,
        "DentalTech/confirm_delete.html",
        {
            "titulo": "Excluir dentista",
            "objeto": profissional.nome,
            "descricao": descricao,
            "impactos": impactos,
            "cancel_url": "DentalTech:dentistas",
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