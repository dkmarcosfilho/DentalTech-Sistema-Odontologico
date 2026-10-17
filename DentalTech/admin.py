from django.contrib import admin

from .models import (
    Agendamento,
    Anamnese,
    Atendimento,
    AtendimentoProcedimento,
    Dente,
    LogAuditoria,
    Odontograma,
    Paciente,
    Procedimento,
    Profissional,
    Prontuario,
    Relatorio,
    Tratamento,
)


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "telefone")
    search_fields = ("nome", "cpf", "telefone", "email")
    filter_horizontal = ("profissionais",)


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ("paciente", "profissional", "data", "horario", "status")
    list_filter = ("status", "profissional", "data")
    search_fields = ("paciente__nome",)


@admin.register(Procedimento)
class ProcedimentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "valor", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    """Trilha de auditoria: somente leitura (ninguém edita ou apaga pelo admin)."""

    list_display = ("criado_em", "usuario_nome", "acao", "modelo", "objeto_repr", "ip")
    list_filter = ("acao", "modelo")
    search_fields = ("usuario_nome", "objeto_repr", "detalhes")
    date_hierarchy = "criado_em"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Profissional)
admin.site.register(Prontuario)
admin.site.register(Odontograma)
admin.site.register(Dente)
admin.site.register(Tratamento)
admin.site.register(Atendimento)
admin.site.register(AtendimentoProcedimento)
admin.site.register(Relatorio)
admin.site.register(Anamnese)
