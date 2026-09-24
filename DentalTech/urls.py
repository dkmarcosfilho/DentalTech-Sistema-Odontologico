from django.urls import path

from . import views

app_name = "DentalTech"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("sair/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("pacientes/", views.paciente_list, name="pacientes"),
    path("pacientes/novo/", views.paciente_create, name="paciente_create"),
    path("pacientes/<int:pk>/", views.paciente_detail, name="paciente_detail"),
    path("pacientes/<int:pk>/editar/", views.paciente_update, name="paciente_update"),
    path("agenda/", views.agendamento_list, name="agenda"),
    path("agenda/novo/", views.agendamento_create, name="agendamento_create"),
    path("agenda/<int:pk>/editar/", views.agendamento_update, name="agendamento_update"),
    path("dentistas/", views.dentistas, name="dentistas"),
    path("dentistas/novo/", views.dentista_create, name="dentista_create"),
    path("dentistas/<int:pk>/editar/", views.dentista_update, name="dentista_update"),
    path("relatorios/", views.relatorios, name="relatorios"),
    path("configuracoes/", views.configuracoes, name="configuracoes"),
    path("agenda/<int:agendamento_id>/atendimento/novo/", views.atendimento_create, name="atendimento_create"),
    path("atendimentos/<int:pk>/", views.atendimento_detail, name="atendimento_detail"),
    path("atendimentos/<int:pk>/editar/", views.atendimento_update, name="atendimento_update"),
]
