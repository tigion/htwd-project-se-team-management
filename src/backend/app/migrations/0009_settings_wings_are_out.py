# Generated by Django 5.0.1 on 2024-02-09 08:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0008_alter_settings_poll_is_visible_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='settings',
            name='wings_are_out',
            field=models.BooleanField(default=False, help_text='Wenn aktiv, werden die Wirtschaftsingenieure (Wings) für Software Engineering II in den Teams nicht mehr angezeigt. Sie nehmen nur an SE I teil.', verbose_name='Wings für SE II ausblenden'),
        ),
    ]