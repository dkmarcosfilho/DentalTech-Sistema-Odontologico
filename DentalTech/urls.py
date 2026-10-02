from django.urls import path

from . import views


urlpatterns = [
    # Autenticação
    path("login/", views.login_view, name="login"),
    path("cadastro/", views.cadastro_view, name="cadastro"),
    path("sair/", views.logout_view, name="logout"),

    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Pacientes
    path("pacientes/", views.paciente_list, name="pacientes"),
    path(
        "pacientes/novo/",
        views.paciente_create,
        name="paciente_create",
    ),
    path(
        "pacientes/<int:pk>/",
        views.paciente_detail,
        name="paciente_detail",
    ),
    path(
        "pacientes/<int:pk>/editar/",
        views.paciente_update,
        name="paciente_update",
    ),

    # Agenda
    path("agenda/", views.agendamento_list, name="agenda"),
    path(
        "agenda/novo/",
        views.agendamento_create,
        name="agendamento_create",
    ),
    path(
        "agenda/<int:pk>/editar/",
        views.agendamento_update,
        name="agendamento_update",
    ),

    # Dentistas
    path("dentistas/", views.dentistas, name="dentistas"),
    path(
        "dentistas/novo/",
        views.dentista_create,
        name="dentista_create",
    ),
    path(
        "dentistas/<int:pk>/editar/",
        views.dentista_update,
        name="dentista_update",
    ),

    # Relatórios e configurações
    path(
        "relatorios/",
        views.relatorios,
        name="relatorios",
    ),
    path(
        "configuracoes/",
        views.configuracoes,
        name="configuracoes",
    ),

    # Atendimentos
    path(
        "agenda/<int:agendamento_id>/atendimento/novo/",
        views.atendimento_create,
        name="atendimento_create",
    ),
    path(
        "atendimentos/<int:pk>/",
        views.atendimento_detail,
        name="atendimento_detail",
    ),
    path(
        "atendimentos/<int:pk>/editar/",
        views.atendimento_update,
        name="atendimento_update",
    ),
]