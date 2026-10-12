"""Regras de acesso: quem pode ver/alterar o quê."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Agendamento, Paciente, Profissional


def usuario_tem_acesso_geral(request):
    return request.user.is_staff or request.user.is_superuser


def get_profissional_logado(request):
    """
    Retorna o profissional ligado ao usuário logado.

    Usuários administrativos (staff/superuser) têm acesso geral
    e retornam None.
    """
    if usuario_tem_acesso_geral(request):
        return None

    try:
        return request.user.profissional
    except Profissional.DoesNotExist:
        raise PermissionDenied(
            "Este usuário ainda não está vinculado a um dentista. "
            "Peça a um administrador para concluir o seu cadastro."
        )


def admin_required(view):
    """Exige login e acesso administrativo."""

    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not usuario_tem_acesso_geral(request):
            raise PermissionDenied(
                "Somente administradores podem acessar esta página."
            )
        return view(request, *args, **kwargs)

    return wrapper


def pacientes_visiveis(request):
    """
    Pacientes que o usuário pode acessar.

    Administradores veem todos; dentistas veem apenas os pacientes
    explicitamente vinculados a eles (Paciente.profissionais).
    """
    profissional = get_profissional_logado(request)
    pacientes = Paciente.objects.all()

    if profissional:
        pacientes = pacientes.filter(profissionais=profissional)

    return pacientes


def get_paciente_ou_404(request, pk):
    return get_object_or_404(pacientes_visiveis(request), pk=pk)


def agendamentos_visiveis(request):
    profissional = get_profissional_logado(request)
    agendamentos = Agendamento.objects.select_related(
        "paciente",
        "profissional",
    )

    if profissional:
        agendamentos = agendamentos.filter(profissional=profissional)

    return agendamentos
