from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0012_precoproduto'),
    ]

    operations = [
        migrations.AddField(
            model_name='precoproduto',
            name='tabela_codigo',
            field=models.CharField(
                max_length=100,
                db_index=True,
                verbose_name='Código da Tabela',
                default=''
            ),
            preserve_default=False,
        ),
    ]
