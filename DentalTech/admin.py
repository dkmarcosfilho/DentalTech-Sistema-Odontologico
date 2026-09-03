from django.contrib import admin
from .models import *

admin.site.register(Paciente)
admin.site.register(Profissional)
admin.site.register(Agendamento)
admin.site.register(Prontuario)
admin.site.register(Odontograma)
admin.site.register(Dente)
admin.site.register(Tratamento)
admin.site.register(Atendimento)
admin.site.register(Procedimento)
admin.site.register(AtendimentoProcedimento)
admin.site.register(Relatorio)
