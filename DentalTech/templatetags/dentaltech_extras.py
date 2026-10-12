from django import template

from ..utils import formatar_cpf, formatar_moeda

register = template.Library()


@register.filter
def cpf(valor):
    """{{ paciente.cpf|cpf }} -> 000.000.000-00"""
    return formatar_cpf(valor)


@register.filter
def moeda(valor):
    """{{ procedimento.valor|moeda }} -> R$ 1.234,50"""
    return formatar_moeda(valor)
