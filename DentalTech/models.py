from django.db import models
from django.contrib.auth.models import User


class Paciente(models.Model):
    nome = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True)
    data_nascimento = models.DateField()
    telefone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


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

    def __str__(self):
        return (
            f"{self.paciente.nome} - "
            f"{self.data} às {self.horario}"
        )


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
    numero = models.PositiveSmallIntegerField()
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
        return f"Dente {self.numero} - {self.status}"


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
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Procedimento Realizado"
        verbose_name_plural = "Procedimentos Realizados"

    def __str__(self):
        return (
            f"{self.procedimento.nome} - "
            f"{self.atendimento}"
        )


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
