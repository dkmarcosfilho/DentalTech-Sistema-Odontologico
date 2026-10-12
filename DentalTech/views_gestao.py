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
# Usuários: aprovação e vínculo com dentistas
# ==========================================================

@admin_required
def usuario_list(request):
    termo = request.GET.get("q", "").strip()
    usuarios = User.objects.select_related("profissional")

    if termo:
        usuarios = usuarios.filter(
            Q(username__icontains=termo)
            | Q(first_name__icontains=termo)
            | Q(email__icontains=termo)
        )

    # Pendentes primeiro (inativos que nunca entraram).
    usuarios = usuarios.order_by("is_active", "username")
    pagina, querystring = paginar(request, usuarios)

    return render(
        request,
        "DentalTech/usuarios/list.html",
        {"pagina": pagina, "querystring": querystring, "termo": termo},
    )


@admin_required
def usuario_aprovar(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    form = AprovarUsuarioForm(request.POST or None)

    if form.is_valid():
        profissional = form.cleaned_data["profissional"]

        with transaction.atomic():
            if not profissional and form.cleaned_data["novo_nome"]:
                profissional = Profissional.objects.create(
                    nome=form.cleaned_data["novo_nome"].strip(),
                    cro=form.cleaned_data["novo_cro"].strip(),
                    email=usuario.email or None,
                )
            if profissional:
                profissional.usuario = usuario
                profissional.save(update_fields=["usuario"])

            usuario.is_active = True
            usuario.save(update_fields=["is_active"])

        registrar(
            request, Acao.ALTEROU, usuario, modelo="Usuário",
            campos=["is_active"],
            detalhes="Acesso aprovado" + (
                f"; vinculado ao dentista {profissional.nome}" if profissional else ""
            ),
        )
        if profissional:
            messages.success(request, f"Acesso de {usuario.username} aprovado como dentista {profissional.nome}.")
        else:
            messages.warning(
                request,
                f"{usuario.username} foi ativado, mas ainda não está vinculado a "
                "um dentista e não verá dados até que isso seja feito.",
            )
        return redirect("DentalTech:usuarios")

    return render(
        request,
        "DentalTech/usuarios/aprovar.html",
        {"form": form, "alvo": usuario},
    )


@admin_required
@require_POST
def usuario_alternar(request, pk):
    usuario = get_object_or_404(User, pk=pk)

    if usuario == request.user:
        messages.error(request, "Você não pode desativar a própria conta.")
        return redirect("DentalTech:usuarios")

    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=["is_active"])
    registrar(
        request, Acao.ALTEROU, usuario, modelo="Usuário", campos=["is_active"],
        detalhes="Conta ativada" if usuario.is_active else "Conta desativada",
    )
    messages.success(
        request,
        f"Conta de {usuario.username} {'ativada' if usuario.is_active else 'desativada'}.",
    )
    return redirect("DentalTech:usuarios")


@admin_required
@require_POST
def usuario_recusar(request, pk):
    """Remove uma solicitação de acesso que nunca foi usada."""
    usuario = get_object_or_404(
        User, pk=pk, is_active=False, last_login__isnull=True,
        profissional__isnull=True,
    )
    registrar(request, Acao.EXCLUIU, usuario, modelo="Usuário",
              detalhes="Solicitação de acesso recusada")
    nome = usuario.username
    usuario.delete()
    messages.success(request, f"Solicitação de {nome} recusada.")
    return redirect("DentalTech:usuarios")


# ==========================================================
# Auditoria
# ==========================================================

@admin_required
def auditoria_list(request):
    logs = LogAuditoria.objects.select_related("usuario", "paciente")

    usuario = request.GET.get("usuario", "").strip()
    acao = request.GET.get("acao", "")
    termo = request.GET.get("paciente", "").strip()
    ini = parse_date(request.GET.get("de", ""))
    fim = parse_date(request.GET.get("ate", ""))

    if usuario:
        logs = logs.filter(usuario_nome__icontains=usuario)
    if acao in dict(Acao.choices):
        logs = logs.filter(acao=acao)
    else:
        acao = ""
    if termo:
        logs = logs.filter(
            Q(objeto_repr__icontains=termo) | Q(paciente__nome__icontains=termo)
        )
    if ini:
        logs = logs.filter(criado_em__date__gte=ini)
    if fim:
        logs = logs.filter(criado_em__date__lte=fim)

    pagina, querystring = paginar(request, logs, por_pagina=50)

    return render(
        request,
        "DentalTech/auditoria/list.html",
        {
            "pagina": pagina,
            "querystring": querystring,
            "acoes": Acao.choices,
            "filtros": {
                "usuario": usuario, "acao": acao, "paciente": termo,
                "de": request.GET.get("de", "") if ini else "",
                "ate": request.GET.get("ate", "") if fim else "",
            },
        },
    )




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
