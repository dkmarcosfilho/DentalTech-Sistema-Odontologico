"""Administração: usuários (aprovação), auditoria e relatórios."""
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from . import relatorios as motor
from .auditoria import registrar
from .forms import RelatorioFiltroForm
from .models import (
    Agendamento,
    Atendimento,
    LogAuditoria,
    Paciente,
    Profissional,
    Relatorio,
)
from .permissoes import admin_required, get_profissional_logado, usuario_tem_acesso_geral
from .utils import paginar

Acao = LogAuditoria.Acao


# ==========================================================
# Relatórios
# ==========================================================

def _csv_seguro(valor):
    """Evita 'injeção de fórmula' quando o CSV é aberto no Excel/Planilhas."""
    texto = str(valor)
    if texto[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + texto
    return texto


@login_required
def relatorios(request):
    profissional = get_profissional_logado(request)
    acesso_geral = profissional is None
    hoje = timezone.localdate()

    tipos = motor.tipos_disponiveis(acesso_geral)
    resultado = None
    if "tipo" in request.GET:
        form = RelatorioFiltroForm(request.GET, tipos=tipos, acesso_geral=acesso_geral)
    else:
        form = RelatorioFiltroForm(
            initial={"data_inicial": hoje.replace(day=1), "data_final": hoje},
            tipos=tipos, acesso_geral=acesso_geral,
        )

    if "tipo" in request.GET and form.is_valid():
        dados = form.cleaned_data
        alvo = profissional or dados.get("profissional")
        resultado = motor.gerar(dados["tipo"], dados["data_inicial"], dados["data_final"], alvo)
        titulo, tipo_modelo, _ = motor.TIPOS[dados["tipo"]]
        descricao = (
            f"Período {dados['data_inicial']:%d/%m/%Y} a {dados['data_final']:%d/%m/%Y}"
            f" · Dentista: {alvo.nome if alvo else 'todos'}"
            f" · {len(resultado['linhas'])} registro(s)"
        )

        if request.GET.get("formato") == "csv":
            registrar(request, Acao.EXPORTOU, modelo="Relatório",
                      detalhes=f"{titulo} (CSV). {descricao}")
            Relatorio.objects.create(tipo=tipo_modelo, titulo=f"{titulo} (CSV)",
                                     descricao=descricao, gerado_por=request.user)
            resposta = HttpResponse(content_type="text/csv; charset=utf-8-sig")
            resposta["Content-Disposition"] = (
                f'attachment; filename="{dados["tipo"]}_{dados["data_inicial"]}_{dados["data_final"]}.csv"'
            )
            resposta.write("\ufeff")  # Excel reconhece os acentos
            escritor = csv.writer(resposta, delimiter=";")
            escritor.writerow(resultado["colunas"])
            for linha in resultado["linhas"]:
                escritor.writerow([_csv_seguro(c) for c in linha])
            return resposta

        if request.GET.get("gerar"):
            registrar(request, Acao.VISUALIZOU, modelo="Relatório",
                      detalhes=f"{titulo}. {descricao}")
            Relatorio.objects.create(tipo=tipo_modelo, titulo=titulo,
                                     descricao=descricao, gerado_por=request.user)

        pagina, querystring = paginar(request, resultado["linhas"], por_pagina=50)
        resultado["pagina"] = pagina
        resultado["querystring"] = querystring

    historico = Relatorio.objects.select_related("gerado_por")
    if not acesso_geral:
        historico = historico.filter(gerado_por=request.user)

    pacientes = (
        Paciente.objects.filter(profissionais=profissional)
        if profissional else Paciente.objects.all()
    )
    agendamentos = Agendamento.objects.all()
    atendimentos = Atendimento.objects.all()
    if profissional:
        agendamentos = agendamentos.filter(profissional=profissional)
        atendimentos = atendimentos.filter(profissional=profissional)

    return render(
        request,
        "DentalTech/relatorios.html",
        {
            "form": form,
            "resultado": resultado,
            "historico": historico[:10],
            "total_pacientes": pacientes.count(),
            "total_dentistas": 1 if profissional else Profissional.objects.count(),
            "total_agendamentos": agendamentos.count(),
            "total_atendimentos": atendimentos.count(),
            "agendamentos_pendentes": agendamentos.filter(
                status__in=Agendamento.STATUS_PENDENTES
            ).count(),
        },
    )
