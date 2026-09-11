from django.urls import path

from . import views

app_name = "DentalTech"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("pacientes/", views.paciente_list, name="pacientes"),
    path("pacientes/novo/", views.paciente_create, name="paciente_create"),
    path("pacientes/<int:pk>/", views.paciente_detail, name="paciente_detail"),
    path("pacientes/<int:pk>/editar/", views.paciente_update, name="paciente_update"),
    path("agenda/", views.agendamento_list, name="agenda"),
    path("agenda/novo/", views.agendamento_create, name="agendamento_create"),
    path("agenda/<int:pk>/editar/", views.agendamento_update, name="agendamento_update"),
    path("agenda/<int:agendamento_id>/atendimento/novo/", views.atendimento_create, name="atendimento_create"),
    path("atendimentos/<int:pk>/", views.atendimento_detail, name="atendimento_detail"),
    path("atendimentos/<int:pk>/editar/", views.atendimento_update, name="atendimento_update"),
]