"""Geração dos relatórios (consultas + totais). Sem dependência de views."""
from django.db.models import Count, Q, Sum

from .models import (
    Agendamento,
    AtendimentoProcedimento,
    Paciente,
    Profissional,
    Relatorio,
)
from .utils import formatar_moeda

# chave -> (título, tipo do registro Relatorio, só admin?)
TIPOS = {
    "agenda": ("Agenda do período", Relatorio.Tipo.ADMINISTRATIVO, False),
    "atendimentos": ("Procedimentos realizados e valores", Relatorio.Tipo.CLINICO, False),
    "pacientes": ("Pacientes cadastrados no período", Relatorio.Tipo.ADMINISTRATIVO, False),
    "producao": ("Produção por dentista", Relatorio.Tipo.ADMINISTRATIVO, True),
}


def tipos_disponiveis(acesso_geral):
    return [
        (chave, titulo)
        for chave, (titulo, _tipo, so_admin) in TIPOS.items()
        if acesso_geral or not so_admin
    ]


def gerar(chave, ini, fim, profissional=None):
    """
    Devolve dict com: titulo, colunas, linhas (lista de listas de texto),
    resumo (lista de (rótulo, valor)).

    `profissional` restringe o relatório a um dentista (obrigatório para
    dentistas comuns; opcional para administradores).
    """
    return _GERADORES[chave](ini, fim, profissional)


def _agenda(ini, fim, prof):
    ags = Agendamento.objects.filter(data__range=(ini, fim)).select_related(
        "paciente", "profissional"
    )
    if prof:
        ags = ags.filter(profissional=prof)
    ags = ags.order_by("data", "horario")

    resumo = [("Total de agendamentos", ags.count())]
    contagem = dict(ags.values_list("status").annotate(n=Count("id")))
    for valor, rotulo in Agendamento.Status.choices:
        resumo.append((rotulo, contagem.get(valor, 0)))

    linhas = [
        [
            a.data.strftime("%d/%m/%Y"), a.horario.strftime("%H:%M"),
            a.paciente.nome, a.profissional.nome,
            a.get_status_display(), a.motivo,
        ]
        for a in ags
    ]
    return {
        "titulo": TIPOS["agenda"][0],
        "colunas": ["Data", "Horário", "Paciente", "Dentista", "Status", "Motivo"],
        "linhas": linhas,
        "resumo": resumo,
    }


def _atendimentos(ini, fim, prof):
    itens = AtendimentoProcedimento.objects.filter(
        atendimento__agendamento__data__range=(ini, fim),
    ).exclude(
        atendimento__status="CANCELADO"
    ).select_related(
        "procedimento", "dente", "atendimento__agendamento__paciente",
        "atendimento__profissional",
    ).order_by("atendimento__agendamento__data", "id")
    if prof:
        itens = itens.filter(atendimento__profissional=prof)

    total = itens.aggregate(t=Sum("valor"))["t"] or 0
    atendimentos = itens.values("atendimento").distinct().count()

    linhas = [
        [
            i.atendimento.agendamento.data.strftime("%d/%m/%Y"),
            i.atendimento.agendamento.paciente.nome,
            i.atendimento.profissional.nome,
            i.procedimento.nome,
            str(i.dente.numero) if i.dente else "",
            formatar_moeda(i.valor),
        ]
        for i in itens
    ]
    return {
        "titulo": TIPOS["atendimentos"][0],
        "colunas": ["Data", "Paciente", "Dentista", "Procedimento", "Dente", "Valor"],
        "linhas": linhas,
        "resumo": [
            ("Atendimentos com procedimentos", atendimentos),
            ("Procedimentos realizados", len(linhas)),
            ("Total", formatar_moeda(total)),
        ],
    }


def _pacientes(ini, fim, prof):
    # Dados mínimos (sem CPF/endereço) para o relatório não virar vazamento.
    pacs = Paciente.objects.filter(data_cadastro__date__range=(ini, fim))
    if prof:
        pacs = pacs.filter(profissionais=prof)
    pacs = pacs.order_by("data_cadastro")

    linhas = [
        [p.data_cadastro.astimezone().strftime("%d/%m/%Y"), p.nome, p.telefone, p.email or ""]
        for p in pacs
    ]
    return {
        "titulo": TIPOS["pacientes"][0],
        "colunas": ["Cadastro", "Paciente", "Telefone", "E-mail"],
        "linhas": linhas,
        "resumo": [("Novos pacientes", len(linhas))],
    }


def _producao(ini, fim, prof):
    profs = Profissional.objects.all()
    if prof:
        profs = profs.filter(pk=prof.pk)

    janela = Q(agendamentos__data__range=(ini, fim))
    profs = profs.annotate(
        total=Count("agendamentos", filter=janela, distinct=True),
        realizadas=Count(
            "agendamentos",
            filter=janela & Q(agendamentos__status="REALIZADA"),
            distinct=True,
        ),
        canceladas=Count(
            "agendamentos",
            filter=janela & Q(agendamentos__status="CANCELADA"),
            distinct=True,
        ),
    ).order_by("nome")

    valores = dict(
        AtendimentoProcedimento.objects.filter(
            atendimento__agendamento__data__range=(ini, fim),
        ).exclude(atendimento__status="CANCELADO")
        .values_list("atendimento__profissional")
        .annotate(t=Sum("valor"))
    )

    linhas, geral = [], 0
    for p in profs:
        valor = valores.get(p.pk) or 0
        geral += valor
        linhas.append([
            p.nome, p.total, p.realizadas, p.canceladas, formatar_moeda(valor),
        ])
    return {
        "titulo": TIPOS["producao"][0],
        "colunas": ["Dentista", "Agendamentos", "Realizadas", "Canceladas", "Valor produzido"],
        "linhas": linhas,
        "resumo": [("Dentistas", len(linhas)), ("Total produzido", formatar_moeda(geral))],
    }


_GERADORES = {
    "agenda": _agenda,
    "atendimentos": _atendimentos,
    "pacientes": _pacientes,
    "producao": _producao,
}
