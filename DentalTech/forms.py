from datetime import datetime

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from django.db.models import Q
from django.utils import timezone

from .models import (
    DENTES_DECIDUOS,
    DENTES_PERMANENTES,
    Agendamento,
    Atendimento,
    AtendimentoProcedimento,
    Odontograma,
    Paciente,
    Procedimento,
    Profissional,
    Prontuario,
    Tratamento,
    Dente,
)
from .utils import formatar_cpf, formatar_moeda, so_digitos


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs.setdefault("format", "%Y-%m-%d")
        super().__init__(**kwargs)


class TimeInput(forms.TimeInput):
    input_type = "time"

    def __init__(self, **kwargs):
        kwargs.setdefault("format", "%H:%M")
        super().__init__(**kwargs)


def _usuario_label(usuario):
    nome = usuario.get_full_name() or usuario.username
    return f"{nome} ({usuario.username})"


CHOICES_DENTES = [("", "— nenhum —")] + [
    ("Permanentes", [(str(n), f"Dente {n}") for n in DENTES_PERMANENTES]),
    ("Decíduos", [(str(n), f"Dente {n}") for n in DENTES_DECIDUOS]),
]


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

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CadastroForm(UserCreationForm):
    email = forms.EmailField(required=True, label="E-mail")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class ProcedimentoForm(forms.ModelForm):
    class Meta:
        model = Procedimento
        fields = ["nome", "descricao", "valor", "ativo"]
        labels = {"valor": "Valor (R$)", "ativo": "Ativo (disponível para novos atendimentos)"}
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "valor": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def clean_valor(self):
        valor = self.cleaned_data["valor"]
        if valor < 0:
            raise forms.ValidationError("O valor não pode ser negativo.")
        return valor

    def clean_nome(self):
        nome = self.cleaned_data["nome"].strip()
        duplicado = Procedimento.objects.filter(nome__iexact=nome)
        if self.instance.pk:
            duplicado = duplicado.exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise forms.ValidationError("Já existe um procedimento com este nome.")
        return nome