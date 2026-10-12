from django.contrib.auth.models import User


def avisos_admin(request):
    """Avisa administradores sobre solicitações de acesso pendentes."""
    usuario = getattr(request, "user", None)

    if not (
        usuario
        and usuario.is_authenticated
        and (usuario.is_staff or usuario.is_superuser)
    ):
        return {}

    return {
        "usuarios_pendentes": User.objects.filter(
            is_active=False,
            last_login__isnull=True,
            profissional__isnull=True,
        ).count(),
    }
