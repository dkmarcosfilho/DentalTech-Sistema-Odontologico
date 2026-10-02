from django import forms
from django.forms import inlineformset_factory

from .models import (
    Agendamento,
    Atendimento,
    AtendimentoProcedimento,
    Paciente,
    Profissional,
)


class DateInput(forms.DateInput):
    input_type = "date"


class TimeInput(forms.TimeInput):
    input_type = "time"


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            "nome",
            "cpf",
            "data_nascimento",
            "telefone",
            "email",
            "endereco",
            "observacoes",
        ]
        widgets = {
            "data_nascimento": DateInput()
        }


class ProfissionalForm(forms.ModelForm):
    class Meta:
        model = Profissional
        fields = [
            "nome",
            "cro",
            "especialidade",
            "telefone",
            "email",
        ]
        labels = {
            "nome": "Nome do dentista",
            "cro": "CRO",
            "especialidade": "Especialidade",
            "telefone": "Telefone",
            "email": "E-mail",
        }


class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = [
            "paciente",
            "profissional",
            "data",
            "horario",
            "status",
            "motivo",
            "observacoes",
        ]
        widgets = {
            "data": DateInput(),
            "horario": TimeInput(),
        }
        labels = {
            "paciente": "Paciente",
            "profissional": "Dentista",
            "data": "Data",
            "horario": "Horário",
            "status": "Status",
            "motivo": "Motivo da consulta",
            "observacoes": "Observações",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["paciente"].queryset = Paciente.objects.order_by("nome")
        self.fields["profissional"].queryset = Profissional.objects.order_by("nome")


class AtendimentoForm(forms.ModelForm):
    class Meta:
        model = Atendimento
        fields = [
            "profissional",
            "descricao",
            "diagnostico",
            "observacoes",
            "status",
        ]


class AtendimentoProcedimentoForm(forms.ModelForm):
    class Meta:
        model = AtendimentoProcedimento
        fields = [
            "procedimento",
            "dente",
            "observacoes",
        ]


AtendimentoProcedimentoFormSet = inlineformset_factory(
    Atendimento,
    AtendimentoProcedimento,
    form=AtendimentoProcedimentoForm,
    extra=1,
    can_delete=True,
)