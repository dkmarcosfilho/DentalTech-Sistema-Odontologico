# Recria a migration 0003 que já estava aplicada no db.sqlite3 local mas não
# existia na pasta de migrations (o model Relatorio estava sem migration).
# O nome é o mesmo registrado em django_migrations para não reaplicar.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DentalTech', '0002_alter_atendimentoprocedimento_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='atendimentoprocedimento',
            options={'verbose_name': 'Procedimento Realizado', 'verbose_name_plural': 'Procedimentos Realizados'},
        ),
        migrations.CreateModel(
            name='Relatorio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('ADMINISTRATIVO', 'Administrativo'), ('CLINICO', 'Clínico')], max_length=20)),
                ('titulo', models.CharField(max_length=150)),
                ('descricao', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('gerado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='relatorios', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Relatório',
                'verbose_name_plural': 'Relatórios',
                'ordering': ['-criado_em'],
            },
        ),
    ]
