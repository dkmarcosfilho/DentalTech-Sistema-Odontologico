"""
Migração de dados:

1. Cria o vínculo dentista↔paciente a partir dos agendamentos existentes
   (era assim que o acesso era "deduzido" antes).
2. Congela o valor cobrado nos procedimentos já realizados.
3. Normaliza os CPFs para somente dígitos.
"""
import re

from django.db import migrations


def _digitos(texto):
    return re.sub(r"\D", "", texto or "")


def popular_dados(apps, schema_editor):
    Agendamento = apps.get_model("DentalTech", "Agendamento")
    AtendimentoProcedimento = apps.get_model("DentalTech", "AtendimentoProcedimento")
    Paciente = apps.get_model("DentalTech", "Paciente")
    Procedimento = apps.get_model("DentalTech", "Procedimento")
    Vinculo = Paciente.profissionais.through

    # 1) vínculo dentista↔paciente
    ja_vinculados = set(
        Vinculo.objects.values_list("paciente_id", "profissional_id")
    )
    novos = [
        Vinculo(paciente_id=paciente_id, profissional_id=profissional_id)
        for paciente_id, profissional_id in (
            Agendamento.objects
            .values_list("paciente_id", "profissional_id")
            .distinct()
        )
        if (paciente_id, profissional_id) not in ja_vinculados
    ]
    Vinculo.objects.bulk_create(novos)

    # 2) valor cobrado = valor atual da tabela, para o histórico existente
    for procedimento in Procedimento.objects.all():
        if procedimento.valor:
            AtendimentoProcedimento.objects.filter(
                procedimento=procedimento,
                valor=0,
            ).update(valor=procedimento.valor)

    # 3) CPF somente com dígitos
    ocupados = {
        cpf for cpf in Paciente.objects.values_list("cpf", flat=True)
        if cpf == _digitos(cpf)
    }
    conflitos = []

    for paciente in Paciente.objects.order_by("id"):
        digitos = _digitos(paciente.cpf)

        if not digitos or digitos == paciente.cpf:
            continue

        if digitos in ocupados:
            # Mesmo CPF digitado de dois jeitos: não dá para decidir sozinho.
            conflitos.append((paciente.pk, paciente.nome, paciente.cpf))
            continue

        Paciente.objects.filter(pk=paciente.pk).update(cpf=digitos)
        ocupados.add(digitos)

    if conflitos:
        print(
            "\n  [ATENÇÃO] Pacientes com CPF duplicado (mesmo número, "
            "formatos diferentes). Revise e una os cadastros:"
        )
        for pk, nome, cpf in conflitos:
            print(f"    - id={pk} {nome} ({cpf})")


class Migration(migrations.Migration):

    dependencies = [
        ("DentalTech", "0004_vinculo_paciente_auditoria_valor"),
    ]

    operations = [
        migrations.RunPython(popular_dados, migrations.RunPython.noop),
    ]
