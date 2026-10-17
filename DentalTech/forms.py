from datetime import datetime

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from django.db.models import Q
from django.utils import timezone


from .anamnese_perguntas import (
    MULTIPLA,
    SECOES,
    TEXTO,
    TODOS_OS_ITENS,
)

from .models import (
    DENTES_DECIDUOS,
    DENTES_PERMANENTES,
    Agendamento,
    Anamnese,
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


# ==========================================================
# Pacientes
# ==========================================================

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
            "profissionais",
        ]
        widgets = {
            "data_nascimento": DateInput(),
            "cpf": forms.TextInput(attrs={
                "data-mask": "cpf",
                "inputmode": "numeric",
                "placeholder": "000.000.000-00",
                "autocomplete": "off",
            }),
            "telefone": forms.TextInput(attrs={
                "data-mask": "telefone",
                "inputmode": "tel",
                "placeholder": "(00) 00000-0000",
            }),
            "profissionais": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, acesso_geral=False, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.initial["cpf"] = formatar_cpf(self.instance.cpf)

        if acesso_geral:
            self.fields["profissionais"].required = False
            self.fields["profissionais"].queryset = Profissional.objects.order_by("nome")
            self.fields["profissionais"].help_text = (
                "Somente estes dentistas poderão ver a ficha do paciente."
            )
        else:
            # Dentista comum: o vínculo é feito pela view (ele mesmo).
            del self.fields["profissionais"]

    def clean_cpf(self):
        cpf = so_digitos(self.cleaned_data["cpf"])
        existe = Paciente.objects.filter(cpf=cpf)

        if self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)

        if existe.exists():
            raise forms.ValidationError(
                "Este CPF já está cadastrado na clínica. Se o paciente deve "
                "ser atendido por você, peça a um administrador para "
                "vinculá-lo ao seu perfil."
            )

        return cpf

    def clean_data_nascimento(self):
        data = self.cleaned_data["data_nascimento"]
        if data > timezone.localdate():
            raise forms.ValidationError("A data de nascimento não pode ser no futuro.")
        return data

# ==========================================================
# Anamnese
# ==========================================================

class AnamneseForm(forms.Form):
    """
    Formulário montado a partir do catálogo (anamnese_perguntas.py):
    uma pergunta no catálogo = um campo aqui. Nada é obrigatório, porque
    o paciente pode ir respondendo aos poucos.
    """

    def __init__(self, *args, anamnese, **kwargs):
        self.anamnese = anamnese
        super().__init__(*args, initial=dict(anamnese.respostas or {}), **kwargs)

        for item in TODOS_OS_ITENS:
            self.fields[item.codigo] = self._campo(item)
            if item.detalhe:
                self.fields[item.codigo_detalhe] = forms.CharField(
                    required=False,
                    max_length=200,
                    label=item.detalhe,
                    widget=forms.TextInput(attrs={"placeholder": item.detalhe}),
                )

    @staticmethod
    def _campo(item):
        if item.tipo == MULTIPLA:
            return forms.MultipleChoiceField(
                required=False,
                label=item.texto,
                choices=item.opcoes,
                widget=forms.CheckboxSelectMultiple,
            )
        if item.tipo == TEXTO:
            return forms.CharField(
                required=False,
                max_length=500,
                label=item.texto,
                widget=forms.Textarea(attrs={"rows": 2}),
            )
        return forms.ChoiceField(
            required=False,
            label=item.texto,
            choices=item.opcoes,
            widget=forms.RadioSelect,
        )

    def secoes(self):
        """Seções com os campos já ligados ao formulário, para o template."""
        resultado = []
        for secao in SECOES:
            linhas = []
            for item in secao.itens:
                linhas.append({
                    "item": item,
                    "campo": self[item.codigo],
                    "detalhe": self[item.codigo_detalhe] if item.detalhe else None,
                    "multipla": item.tipo == MULTIPLA,
                    "texto": item.tipo == TEXTO,
                })
            resultado.append({"secao": secao, "linhas": linhas})
        return resultado

    def salvar(self):
        respostas = {}
        for nome, valor in self.cleaned_data.items():
            if isinstance(valor, str):
                valor = valor.strip()
            if valor in ("", [], None):
                continue
            respostas[nome] = valor

        self.anamnese.respostas = respostas
        self.anamnese.preenchida = True
        self.anamnese.save()
        return self.anamnese


# ==========================================================
# Dentistas e usuários
# ==========================================================

class ProfissionalForm(forms.ModelForm):
    usuario = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Usuário de acesso",
        help_text=(
            "Vincule uma conta existente para que este dentista possa entrar "
            "no sistema. Contas novas precisam ser aprovadas na tela Usuários."
        ),
    )

    class Meta:
        model = Profissional
        fields = [
            "nome",
            "cro",
            "especialidade",
            "telefone",
            "email",
            "usuario",
        ]
        labels = {
            "nome": "Nome do dentista",
            "cro": "CRO",
            "especialidade": "Especialidade",
            "telefone": "Telefone",
            "email": "E-mail",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        livres = Q(profissional__isnull=True)
        if self.instance.pk:
            livres |= Q(profissional=self.instance)
        campo = self.fields["usuario"]
        campo.queryset = User.objects.filter(is_active=True).filter(livres).order_by("username")
        campo.label_from_instance = _usuario_label

class CadastroForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="Nome completo")
    email = forms.EmailField(required=True, label="E-mail")

    class Meta:
        model = User
        fields = ("username", "first_name", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.email = self.cleaned_data["email"]
        usuario.first_name = self.cleaned_data["first_name"]
        # Só entra depois que um administrador aprovar.
        usuario.is_active = False
        if commit:
            usuario.save()
        return usuario


class AprovarUsuarioForm(forms.Form):
    profissional = forms.ModelChoiceField(
        queryset=Profissional.objects.none(),
        required=False,
        label="Vincular a um dentista já cadastrado",
    )
    novo_nome = forms.CharField(max_length=150, required=False, label="Ou cadastrar novo dentista: nome")
    novo_cro = forms.CharField(max_length=20, required=False, label="CRO do novo dentista")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profissional"].queryset = Profissional.objects.filter(
            usuario__isnull=True
        ).order_by("nome")

    def clean(self):
        dados = super().clean()
        nome = (dados.get("novo_nome") or "").strip()
        cro = (dados.get("novo_cro") or "").strip()

        if dados.get("profissional") and (nome or cro):
            raise forms.ValidationError(
                "Escolha um dentista existente OU cadastre um novo, não os dois."
            )
        if bool(nome) != bool(cro):
            self.add_error(
                "novo_cro" if nome else "novo_nome",
                "Informe nome e CRO para cadastrar um novo dentista.",
            )
        if cro and Profissional.objects.filter(cro__iexact=cro).exists():
            self.add_error("novo_cro", "Já existe um dentista com este CRO.")
        return dados




# ==========================================================
# Agenda
# ==========================================================

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

    def __init__(self, *args, profissional=None, **kwargs):
        """
        profissional: dentista logado. Quando informado, o campo "Dentista"
        some do formulário (ele só agenda para si) e a lista de pacientes
        mostra apenas os pacientes vinculados a ele.
        """
        super().__init__(*args, **kwargs)
        self.profissional_fixo = profissional

        if profissional:
            del self.fields["profissional"]
            pacientes = profissional.pacientes.order_by("nome")
        else:
            self.fields["profissional"].queryset = Profissional.objects.order_by("nome")
            self.fields["profissional"].required = True
            pacientes = Paciente.objects.order_by("nome")

        self.fields["paciente"].queryset = pacientes

        # "Realizada" só nasce de um atendimento registrado.
        if self.instance.status != Agendamento.Status.REALIZADA:
            self.fields["status"].choices = [
                c for c in Agendamento.Status.choices
                if c[0] != Agendamento.Status.REALIZADA
            ]

    def clean(self):
        dados = super().clean()
        data = dados.get("data")
        horario = dados.get("horario")
        status = dados.get("status")
        paciente = dados.get("paciente")
        profissional = self.profissional_fixo or dados.get("profissional")

        if not (data and horario):
            return dados

        mudou_horario = (
            self.instance.pk is None
            or self.instance.data != data
            or self.instance.horario != horario
        )

        if (
            status in Agendamento.STATUS_PENDENTES
            and mudou_horario
            and timezone.make_aware(datetime.combine(data, horario)) < timezone.now()
        ):
            self.add_error(None, "Não é possível agendar em um horário que já passou.")

        if status in Agendamento.STATUS_LIBERAM_HORARIO or not profissional:
            return dados

        outros = Agendamento.objects.filter(
            data=data, horario=horario
        ).exclude(status__in=Agendamento.STATUS_LIBERAM_HORARIO)
        if self.instance.pk:
            outros = outros.exclude(pk=self.instance.pk)

        if outros.filter(profissional=profissional).exists():
            self.add_error(
                None,
                "Este dentista já tem um agendamento neste horário. "
                "Escolha outro horário.",
            )
        elif paciente and outros.filter(paciente=paciente).exists():
            self.add_error(
                None,
                "Este paciente já tem outro agendamento neste mesmo horário.",
            )

        return dados

    def validate_constraints(self):
        # O conflito de horário já foi explicado em clean(); a regra do
        # banco continua valendo como segunda barreira.
        if self._errors:
            return
        super().validate_constraints()


class _DentePorNumeroMixin:
    """Escolhe o dente pelo número (FDI); o registro é criado sob demanda."""

    def _configurar_dente(self, paciente):
        self.paciente = paciente
        self.fields["dente_numero"] = forms.ChoiceField(
            choices=CHOICES_DENTES, required=False, label="Dente",
        )
        dente = getattr(self.instance, "dente", None) if self.instance.pk else None
        if dente:
            self.initial["dente_numero"] = str(dente.numero)

    def _dente(self):
        numero = self.cleaned_data.get("dente_numero")
        if not numero:
            return None
        return self.paciente.obter_dente(int(numero))


# ==========================================================
# Atendimentos
# ==========================================================

class AtendimentoForm(forms.ModelForm):
    class Meta:
        model = Atendimento
        fields = ["descricao", "diagnostico", "observacoes", "status"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "diagnostico": forms.Textarea(attrs={"rows": 3}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class _DentePorNumeroMixin:
    """Escolhe o dente pelo número (FDI); o registro é criado sob demanda."""

    def _configurar_dente(self, paciente):
        self.paciente = paciente
        self.fields["dente_numero"] = forms.ChoiceField(
            choices=CHOICES_DENTES, required=False, label="Dente",
        )
        dente = getattr(self.instance, "dente", None) if self.instance.pk else None
        if dente:
            self.initial["dente_numero"] = str(dente.numero)

    def _dente(self):
        numero = self.cleaned_data.get("dente_numero")
        if not numero:
            return None
        return self.paciente.obter_dente(int(numero))


class AtendimentoProcedimentoForm(_DentePorNumeroMixin, forms.ModelForm):
    class Meta:
        model = AtendimentoProcedimento
        fields = ["procedimento", "observacoes"]
        widgets = {"observacoes": forms.TextInput()}

    def __init__(self, *args, paciente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._configurar_dente(paciente)
        filtro = Q(ativo=True)
        if self.instance.pk:
            filtro |= Q(pk=self.instance.procedimento_id)
        campo = self.fields["procedimento"]
        campo.queryset = Procedimento.objects.filter(filtro)
        campo.label_from_instance = lambda p: f"{p.nome} — {formatar_moeda(p.valor)}"
        self.order_fields(["procedimento", "dente_numero", "observacoes"])

    def save(self, commit=True):
        objeto = super().save(commit=False)
        objeto.dente = self._dente()
        if commit:
            objeto.save()
        return objeto


AtendimentoProcedimentoFormSet = inlineformset_factory(
    Atendimento,
    AtendimentoProcedimento,
    form=AtendimentoProcedimentoForm,
    extra=1,
    can_delete=True,
)


# ==========================================================
# Clínico: prontuário, odontograma, tratamentos, procedimentos
# ==========================================================

class ProntuarioForm(forms.ModelForm):
    class Meta:
        model = Prontuario
        fields = [
            "alergias",
            "medicamentos",
            "historico_medico",
            "historico_odontologico",
            "observacoes",
        ]
        widgets = {nome: forms.Textarea(attrs={"rows": 4}) for nome in fields}
        labels = {
            "alergias": "Alergias",
            "medicamentos": "Medicamentos em uso",
            "historico_medico": "Histórico médico",
            "historico_odontologico": "Histórico odontológico",
            "observacoes": "Observações",
        }

class OdontogramaObservacoesForm(forms.ModelForm):
    class Meta:
        model = Odontograma
        fields = ["observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 3})}
        labels = {"observacoes": "Observações gerais do odontograma"}


class DenteForm(forms.ModelForm):
    class Meta:
        model = Dente
        fields = ["status", "observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 3})}



class TratamentoForm(_DentePorNumeroMixin, forms.ModelForm):
    class Meta:
        model = Tratamento
        fields = [
            "nome", "diagnostico", "descricao",
            "data_inicio", "data_conclusao", "concluido",
        ]
        widgets = {
            "diagnostico": forms.Textarea(attrs={"rows": 3}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "data_inicio": DateInput(),
            "data_conclusao": DateInput(),
        }

    def __init__(self, *args, paciente, **kwargs):
        super().__init__(*args, **kwargs)
        self._configurar_dente(paciente)
        self.order_fields(["nome", "dente_numero"])

    def clean(self):
        dados = super().clean()
        inicio = dados.get("data_inicio")
        fim = dados.get("data_conclusao")

        if inicio and fim and fim < inicio:
            self.add_error("data_conclusao", "A conclusão não pode ser antes do início.")
        if dados.get("concluido") and not fim:
            dados["data_conclusao"] = timezone.localdate()
        return dados

    def save(self, commit=True):
        tratamento = super().save(commit=False)
        tratamento.odontograma, _ = Odontograma.objects.get_or_create(paciente=self.paciente)
        tratamento.dente = self._dente()
        if commit:
            tratamento.save()
        return tratamento


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

# ==========================================================
# Relatórios
# ==========================================================

class RelatorioFiltroForm(forms.Form):
    tipo = forms.ChoiceField(label="Relatório", choices=[])
    data_inicial = forms.DateField(label="De", widget=DateInput())
    data_final = forms.DateField(label="Até", widget=DateInput())
    profissional = forms.ModelChoiceField(
        queryset=Profissional.objects.order_by("nome"),
        required=False,
        label="Dentista",
        empty_label="Todos os dentistas",
    )

    def __init__(self, *args, tipos, acesso_geral, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].choices = tipos
        if not acesso_geral:
            del self.fields["profissional"]

    def clean(self):
        dados = super().clean()
        ini, fim = dados.get("data_inicial"), dados.get("data_final")
        if ini and fim:
            if fim < ini:
                raise forms.ValidationError("A data final não pode ser antes da inicial.")
            if (fim - ini).days > 366:
                raise forms.ValidationError("Escolha um período de até 1 ano.")
        return dados
