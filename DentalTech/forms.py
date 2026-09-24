from django import forms
from django.forms import inlineformset_factory

from .models import (
    Agendamento,
    Atendimento,
    AtendimentoProcedimento,
    Paciente,
)


class DateInput(forms.DateInput):
    input_type = "date"


class TimeInput(forms.TimeInput):
    input_type = "time"


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            "nome", "cpf", "data_nascimento", "telefone", "email",
            "endereco", "observacoes",
        ]
        widgets = {"data_nascimento": DateInput()}


class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = [
            "paciente", "profissional", "data", "horario", "status",
            "motivo", "observacoes",
        ]
        widgets = {"data": DateInput(), "horario": TimeInput()}


class AtendimentoForm(forms.ModelForm):
    class Meta:
        model = Atendimento
        fields = ["profissional", "descricao", "diagnostico", "observacoes", "status"]


class AtendimentoProcedimentoForm(forms.ModelForm):
    class Meta:
        model = AtendimentoProcedimento
        fields = ["procedimento", "dente", "observacoes"]


AtendimentoProcedimentoFormSet = inlineformset_factory(
    Atendimento,
    AtendimentoProcedimento,
    form=AtendimentoProcedimentoForm,
    extra=1,
    can_delete=True,
)