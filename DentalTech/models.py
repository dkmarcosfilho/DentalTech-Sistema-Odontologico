from datetime import date, datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from .utils import cpf_valido, formatar_cpf, so_digitos


# ==========================================================
# Numeração dos dentes (notação FDI / ISO 3950)
# ==========================================================

DENTES_PERMANENTES = (
    list(range(11, 19)) + list(range(21, 29))
    + list(range(31, 39)) + list(range(41, 49))
)

DENTES_DECIDUOS = (
    list(range(51, 56)) + list(range(61, 66))
    + list(range(71, 76)) + list(range(81, 86))
)

TODOS_OS_DENTES = DENTES_PERMANENTES + DENTES_DECIDUOS


def validar_cpf(valor):
    if not cpf_valido(valor):
        raise ValidationError("Informe um CPF válido.")


def validar_numero_dente(valor):
    if valor not in TODOS_OS_DENTES:
        raise ValidationError(
            "Número de dente inválido (use a notação FDI, ex.: 18, 21, 46, 55)."
        )


class Paciente(models.Model):
    nome = models.CharField(max_length=150)
    # Guardado somente com dígitos (11 caracteres). A máscara é só visual.
    cpf = models.CharField(
        max_length=14,
        unique=True,
        validators=[validar_cpf],
        verbose_name="CPF",
    )
    data_nascimento = models.DateField()
    telefone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    # Vínculo EXPLÍCITO entre dentistas e pacientes: define quem pode
    # acessar a ficha. Não depende mais de existir um agendamento.
    profissionais = models.ManyToManyField(
        "Profissional",
        related_name="pacientes",
        blank=True,
        verbose_name="Dentistas responsáveis",
    )

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        # "111.111.111-11" e "11111111111" são o mesmo CPF.
        self.cpf = so_digitos(self.cpf)
        super().save(*args, **kwargs)

    @property
    def cpf_formatado(self):
        return formatar_cpf(self.cpf)

    @property
    def idade(self):
        hoje = timezone.localdate()
        nasc = self.data_nascimento
        return hoje.year - nasc.year - (
            (hoje.month, hoje.day) < (nasc.month, nasc.day)
        )

    def obter_dente(self, numero):
        """Devolve (criando se preciso) o dente do odontograma do paciente."""
        with transaction.atomic():
            odontograma, _ = Odontograma.objects.get_or_create(paciente=self)
            dente, _ = Dente.objects.get_or_create(
                odontograma=odontograma,
                numero=numero,
            )
        return dente


class Profissional(models.Model):
    nome = models.CharField(max_length=150)
    cro = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="CRO"
    )
    especialidade = models.CharField(max_length=100, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, null=True)
    usuario = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profissional"
    )

    class Meta:
        verbose_name = "Profissional"
        verbose_name_plural = "Profissionais"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} - CRO {self.cro}"


class Agendamento(models.Model):

    class Status(models.TextChoices):
        AGENDADA = "AGENDADA", "Agendada"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        REALIZADA = "REALIZADA", "Realizada"
        CANCELADA = "CANCELADA", "Cancelada"
        REMARCADA = "REMARCADA", "Remarcada"

    # Estados em que a consulta ainda vai acontecer.
    STATUS_PENDENTES = ("AGENDADA", "CONFIRMADA")
    # Estados que liberam o horário para outro paciente.
    STATUS_LIBERAM_HORARIO = ("CANCELADA", "REMARCADA")

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="agendamentos"
    )
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.PROTECT,
        related_name="agendamentos"
    )
    data = models.DateField()
    horario = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AGENDADA
    )
    motivo = models.CharField(max_length=255, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ["data", "horario"]
        indexes = [
            models.Index(fields=["data", "horario"], name="agend_data_horario_idx"),
            models.Index(fields=["profissional", "data"], name="agend_prof_data_idx"),
        ]
        constraints = [
            # Garantia no banco (vale até para requisições simultâneas):
            # um dentista não pode ter dois agendamentos ativos no mesmo
            # horário. Cancelados/remarcados liberam o horário.
            models.UniqueConstraint(
                fields=["profissional", "data", "horario"],
                condition=~Q(status__in=["CANCELADA", "REMARCADA"]),
                name="agendamento_horario_unico_por_profissional",
                violation_error_message=(
                    "Este dentista já tem um agendamento neste horário."
                ),
            ),
        ]

    def __str__(self):
        return (
            f"{self.paciente.nome} - "
            f"{self.data} às {self.horario}"
        )

    @property
    def inicio(self):
        """Data e hora do agendamento, no fuso da clínica."""
        return timezone.make_aware(datetime.combine(self.data, self.horario))

    @property
    def atendimento_registrado(self):
        return Atendimento.objects.filter(agendamento=self).first()


class Prontuario(models.Model):
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name="prontuario"
    )
    alergias = models.TextField(blank=True)
    medicamentos = models.TextField(blank=True)
    historico_medico = models.TextField(blank=True)
    historico_odontologico = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prontuário"
        verbose_name_plural = "Prontuários"

    def __str__(self):
        return f"Prontuário de {self.paciente.nome}"


class Anamnese(models.Model):
    """
    Anamnese do paciente (questionário de saúde, páginas 9 e 10 da ficha
    da clínica). Cada paciente tem a sua, criada junto com o cadastro.

    As respostas ficam em `respostas`, por código de pergunta (veja
    anamnese_perguntas.py). Pergunta sem resposta simplesmente não aparece.
    """
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name="anamnese"
    )
    respostas = models.JSONField(default=dict, blank=True)
    # Vira True na primeira vez que o formulário é salvo.
    preenchida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Anamnese"
        verbose_name_plural = "Anamneses"

    def __str__(self):
        return f"Anamnese de {self.paciente.nome}"


class Odontograma(models.Model):
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name="odontograma"
    )
    observacoes = models.TextField(blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Odontograma"
        verbose_name_plural = "Odontogramas"

    def __str__(self):
        return f"Odontograma de {self.paciente.nome}"


class Dente(models.Model):

    class Status(models.TextChoices):
        SAUDAVEL = "SAUDAVEL", "Saudável"
        CARIE = "CARIE", "Cárie"
        RESTAURADO = "RESTAURADO", "Restaurado"
        AUSENTE = "AUSENTE", "Ausente"
        EXTRAIDO = "EXTRAIDO", "Extraído"
        FRATURADO = "FRATURADO", "Fraturado"
        OUTRO = "OUTRO", "Outro"

    odontograma = models.ForeignKey(
        Odontograma,
        on_delete=models.CASCADE,
        related_name="dentes"
    )
    numero = models.PositiveSmallIntegerField(
        validators=[validar_numero_dente],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SAUDAVEL
    )
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Dente"
        verbose_name_plural = "Dentes"
        constraints = [
            models.UniqueConstraint(
                fields=["odontograma", "numero"],
                name="dente_unico_por_odontograma"
            )
        ]
        ordering = ["numero"]

    def __str__(self):
        return f"Dente {self.numero} - {self.get_status_display()}"


class Tratamento(models.Model):
    odontograma = models.ForeignKey(
        Odontograma,
        on_delete=models.CASCADE,
        related_name="tratamentos"
    )
    dente = models.ForeignKey(
        Dente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tratamentos"
    )
    nome = models.CharField(max_length=150)
    diagnostico = models.TextField(blank=True)
    descricao = models.TextField(blank=True)
    data_inicio = models.DateField(null=True, blank=True)
    data_conclusao = models.DateField(null=True, blank=True)
    concluido = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Tratamento"
        verbose_name_plural = "Tratamentos"
        ordering = ["concluido", "-data_inicio", "-id"]

    def __str__(self):
        return self.nome


class Atendimento(models.Model):

    class Status(models.TextChoices):
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        CONCLUIDO = "CONCLUIDO", "Concluído"
        CANCELADO = "CANCELADO", "Cancelado"

    agendamento = models.OneToOneField(
        Agendamento,
        on_delete=models.PROTECT,
        related_name="atendimento"
    )
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.PROTECT,
        related_name="atendimentos"
    )
    data = models.DateTimeField(auto_now_add=True)
    descricao = models.TextField()
    diagnostico = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONCLUIDO
    )

    class Meta:
        verbose_name = "Atendimento"
        verbose_name_plural = "Atendimentos"
        ordering = ["-data"]

    def __str__(self):
        return (
            f"Atendimento - "
            f"{self.agendamento.paciente.nome}"
        )

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.sincronizar_agendamento()

    def sincronizar_agendamento(self):
        """
        Registrar um atendimento muda o status do agendamento sozinho:
        vira "Realizada" (ou "Cancelada", se o atendimento foi cancelado).
        """
        if self.status == self.Status.CANCELADO:
            novo_status = Agendamento.Status.CANCELADA
        else:
            novo_status = Agendamento.Status.REALIZADA

        agendamento = self.agendamento
        if agendamento.status != novo_status:
            agendamento.status = novo_status
            agendamento.save(update_fields=["status", "atualizado_em"])


class Procedimento(models.Model):
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Procedimento"
        verbose_name_plural = "Procedimentos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class AtendimentoProcedimento(models.Model):
    atendimento = models.ForeignKey(
        Atendimento,
        on_delete=models.CASCADE,
        related_name="procedimentos"
    )
    procedimento = models.ForeignKey(
        Procedimento,
        on_delete=models.PROTECT,
        related_name="atendimentos"
    )
    dente = models.ForeignKey(
        Dente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procedimentos_realizados"
    )
    # Preço cobrado no momento do atendimento. Sem isso, reajustar o preço
    # do procedimento alteraria retroativamente o histórico financeiro.
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        editable=False,
    )
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Procedimento Realizado"
        verbose_name_plural = "Procedimentos Realizados"

    def __str__(self):
        return (
            f"{self.procedimento.nome} - "
            f"{self.atendimento}"
        )

    def save(self, *args, **kwargs):
        # Congela o preço da tabela na hora do registro (ou se o
        # procedimento for trocado). Reajustes futuros não mudam o histórico.
        if self._state.adding:
            self.valor = self.procedimento.valor
        else:
            anterior = (
                type(self).objects
                .filter(pk=self.pk)
                .values_list("procedimento_id", flat=True)
                .first()
            )
            if anterior != self.procedimento_id:
                self.valor = self.procedimento.valor
        super().save(*args, **kwargs)


class Relatorio(models.Model):

    class Tipo(models.TextChoices):
        ADMINISTRATIVO = "ADMINISTRATIVO", "Administrativo"
        CLINICO = "CLINICO", "Clínico"

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices
    )
    titulo = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    gerado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="relatorios"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Relatório"
        verbose_name_plural = "Relatórios"
        ordering = ["-criado_em"]

    def __str__(self):
        return self.titulo


class LogAuditoria(models.Model):
    """
    Trilha de auditoria (LGPD): quem viu, criou, alterou ou excluiu
    dados de pacientes, e quando.

    Guarda só os NOMES dos campos alterados, nunca os valores, para o
    log não virar uma segunda cópia de dados de saúde.
    """

    class Acao(models.TextChoices):
        VISUALIZOU = "VISUALIZOU", "Visualizou"
        CRIOU = "CRIOU", "Criou"
        ALTEROU = "ALTEROU", "Alterou"
        EXCLUIU = "EXCLUIU", "Excluiu"
        EXPORTOU = "EXPORTOU", "Exportou"
        LOGIN = "LOGIN", "Entrou no sistema"
        LOGOUT = "LOGOUT", "Saiu do sistema"
        LOGIN_FALHOU = "LOGIN_FALHOU", "Tentativa de login falhou"

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # Cópia do nome: o registro continua legível se o usuário for apagado.
    usuario_nome = models.CharField(max_length=150, blank=True)
    acao = models.CharField(max_length=20, choices=Acao.choices)
    modelo = models.CharField(max_length=60, blank=True)
    objeto_id = models.CharField(max_length=40, blank=True)
    objeto_repr = models.CharField(max_length=255, blank=True)
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    detalhes = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Log de auditoria"
        verbose_name_plural = "Logs de auditoria"
        ordering = ["-criado_em", "-id"]
        indexes = [
            models.Index(fields=["paciente", "-criado_em"], name="log_paciente_idx"),
        ]

    def __str__(self):
        return (
            f"{self.criado_em:%d/%m/%Y %H:%M} · "
            f"{self.usuario_nome or 'anônimo'} · "
            f"{self.get_acao_display()} {self.modelo}"
        )
