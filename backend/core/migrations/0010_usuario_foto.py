from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_configuracionsistema_formato_hv_aprobado_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='foto',
            field=models.FileField(blank=True, null=True, upload_to='usuarios/fotos/', verbose_name='Foto de perfil'),
        ),
    ]
