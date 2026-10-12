from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from .auditoria import registrar
from .models import LogAuditoria


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    registrar(request, LogAuditoria.Acao.LOGIN, usuario=user)


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if user is not None:
        registrar(request, LogAuditoria.Acao.LOGOUT, usuario=user)


@receiver(user_login_failed)
def log_login_falhou(sender, credentials, request=None, **kwargs):
    registrar(
        request,
        LogAuditoria.Acao.LOGIN_FALHOU,
        usuario_nome=str(credentials.get("username", ""))[:150],
    )
