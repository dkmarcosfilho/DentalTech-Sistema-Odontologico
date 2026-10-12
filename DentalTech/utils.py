"""Funções utilitárias compartilhadas (CPF, moeda, paginação)."""
import re
from decimal import Decimal

from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


# ----------------------------------------------------------
# CPF
# ----------------------------------------------------------

def so_digitos(valor):
    """Remove tudo que não for dígito (máscara, espaços, pontos...)."""
    return re.sub(r"\D", "", valor or "")


def cpf_valido(valor):
    """Valida o CPF pelos dígitos verificadores. Aceita com ou sem máscara."""
    cpf = so_digitos(valor)

    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    for posicao in (9, 10):
        soma = sum(
            int(cpf[i]) * (posicao + 1 - i)
            for i in range(posicao)
        )
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[posicao]):
            return False

    return True


def formatar_cpf(valor):
    """000.000.000-00 (devolve o valor original se não tiver 11 dígitos)."""
    cpf = so_digitos(valor)
    if len(cpf) != 11:
        return valor or ""
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


# ----------------------------------------------------------
# Moeda
# ----------------------------------------------------------

def formatar_moeda(valor):
    """1234.5 -> 'R$ 1.234,50'."""
    valor = Decimal(valor or 0)
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


# ----------------------------------------------------------
# Paginação
# ----------------------------------------------------------

def paginar(request, queryset, por_pagina=None):
    """
    Pagina um queryset/lista com base em ?page=N.

    Devolve (pagina, querystring), onde querystring contém os demais
    filtros da URL (sem "page") para montar os links de navegação.
    """
    por_pagina = por_pagina or getattr(settings, "ITENS_POR_PAGINA", 20)
    paginator = Paginator(queryset, por_pagina)
    numero = request.GET.get("page", 1)

    try:
        pagina = paginator.page(numero)
    except PageNotAnInteger:
        pagina = paginator.page(1)
    except EmptyPage:
        pagina = paginator.page(paginator.num_pages)

    parametros = request.GET.copy()
    parametros.pop("page", None)
    parametros.pop("gerar", None)
    querystring = parametros.urlencode()

    return pagina, querystring
