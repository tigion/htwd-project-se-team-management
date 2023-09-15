# Generated by Django 4.2.5 on 2023-09-15 10:32

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Settings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('projects_is_visible', models.BooleanField(default=False)),
                ('poll_is_visible', models.BooleanField(default=False)),
                ('poll_is_writable', models.BooleanField(default=False)),
                ('teams_is_visible', models.BooleanField(default=False)),
                ('team_min_member', models.IntegerField(default=6, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(20)])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('s_number', models.CharField(max_length=8, unique=True)),
                ('first_name', models.CharField(max_length=255)),
                ('last_name', models.CharField(max_length=255)),
                ('study_program', models.CharField(choices=[('041', 'Informatik (041)'), ('042', 'Wirtschaftsinformatik (042)'), ('048', 'Verwaltungsinformatik (048)'), ('072', 'Wirtschaftsingenieurwesen (072)')], max_length=3)),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('i', 'Intern'), ('e', 'Extern')], default=('i', 'Intern'), max_length=1)),
                ('number', models.IntegerField(help_text='Type und Nummer ergeben eine eindeutige ProjektID (bspw. I4, E2)', verbose_name='Nummer')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('technologies', models.CharField(blank=True, max_length=255, null=True)),
                ('company', models.CharField(blank=True, max_length=255, null=True)),
                ('contact', models.CharField(blank=True, max_length=255, null=True)),
                ('url', models.URLField(blank=True, null=True)),
            ],
            options={
                'ordering': ('type', 'number'),
                'unique_together': {('type', 'number')},
            },
        ),
    ]
