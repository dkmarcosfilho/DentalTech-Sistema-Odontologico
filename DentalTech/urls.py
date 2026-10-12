from django.urls import path

from . import views, views_clinico, views_gestao

app_name = "DentalTech"

urlpatterns = [
    # Autenticação
    path("login/", views.login_view, name="login"),
    path("cadastro/", views.cadastro_view, name="cadastro"),
    path("sair/", views.logout_view, name="logout"),

    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Pacientes
    path("pacientes/", views.paciente_list, name="pacientes"),
    path("pacientes/novo/", views.paciente_create, name="paciente_create"),
    path("pacientes/<int:pk>/", views.paciente_detail, name="paciente_detail"),
    path("pacientes/<int:pk>/editar/", views.paciente_update, name="paciente_update"),
    path("pacientes/<int:pk>/excluir/", views.paciente_delete, name="paciente_delete"),

    # Prontuário, odontograma, dentes e tratamentos
    path("pacientes/<int:pk>/prontuario/", views_clinico.prontuario_detail, name="prontuario"),
    path("pacientes/<int:pk>/prontuario/editar/", views_clinico.prontuario_update, name="prontuario_update"),
    path("pacientes/<int:pk>/odontograma/", views_clinico.odontograma_detail, name="odontograma"),
    path("pacientes/<int:pk>/odontograma/dente/<int:numero>/", views_clinico.dente_update, name="dente_update"),
    path("pacientes/<int:pk>/tratamentos/", views_clinico.tratamento_list, name="tratamentos"),
    path("pacientes/<int:pk>/tratamentos/novo/", views_clinico.tratamento_create, name="tratamento_create"),
    path("pacientes/<int:pk>/tratamentos/<int:tratamento_id>/editar/", views_clinico.tratamento_update, name="tratamento_update"),
    path("pacientes/<int:pk>/tratamentos/<int:tratamento_id>/concluir/", views_clinico.tratamento_concluir, name="tratamento_concluir"),
    path("pacientes/<int:pk>/tratamentos/<int:tratamento_id>/excluir/", views_clinico.tratamento_delete, name="tratamento_delete"),

    # Procedimentos (cadastro e preços)
    path("procedimentos/", views_clinico.procedimento_list, name="procedimentos"),
    path("procedimentos/novo/", views_clinico.procedimento_create, name="procedimento_create"),
    path("procedimentos/<int:pk>/editar/", views_clinico.procedimento_update, name="procedimento_update"),

    # Agenda
    path("agenda/", views.agendamento_list, name="agenda"),
    path("agenda/novo/", views.agendamento_create, name="agendamento_create"),
    path("agenda/<int:pk>/editar/", views.agendamento_update, name="agendamento_update"),
    path("agenda/<int:pk>/status/<str:novo_status>/", views.agendamento_status, name="agendamento_status"),
    path("agenda/<int:pk>/excluir/", views.agendamento_delete, name="agendamento_delete"),

    # Dentistas
    path("dentistas/", views.dentistas, name="dentistas"),
    path("dentistas/novo/", views.dentista_create, name="dentista_create"),
    path("dentistas/<int:pk>/editar/", views.dentista_update, name="dentista_update"),
    path("dentistas/<int:pk>/excluir/", views.dentista_delete, name="dentista_delete"),

    # Administração
    path("usuarios/", views_gestao.usuario_list, name="usuarios"),
    path("usuarios/<int:pk>/aprovar/", views_gestao.usuario_aprovar, name="usuario_aprovar"),
    path("usuarios/<int:pk>/alternar/", views_gestao.usuario_alternar, name="usuario_alternar"),
    path("usuarios/<int:pk>/recusar/", views_gestao.usuario_recusar, name="usuario_recusar"),
    path("auditoria/", views_gestao.auditoria_list, name="auditoria"),

    # Relatórios e configurações
    path("relatorios/", views_gestao.relatorios, name="relatorios"),
    path("configuracoes/", views.configuracoes, name="configuracoes"),

    # Atendimentos
    path("agenda/<int:agendamento_id>/atendimento/novo/", views.atendimento_create, name="atendimento_create"),
    path("atendimentos/<int:pk>/", views.atendimento_detail, name="atendimento_detail"),
    path("atendimentos/<int:pk>/editar/", views.atendimento_update, name="atendimento_update"),
]
