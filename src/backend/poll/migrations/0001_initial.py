# Generated by Django 4.2.5 on 2023-09-15 10:32

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Poll',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='app.student')),
            ],
        ),
        migrations.CreateModel(
            name='RoleAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.PositiveIntegerField(default=3, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='poll.poll')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.role')),
            ],
            options={
                'unique_together': {('poll', 'role')},
            },
        ),
        migrations.CreateModel(
            name='ProjectAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.PositiveIntegerField(default=3, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='poll.poll')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.project')),
            ],
            options={
                'unique_together': {('poll', 'project')},
            },
        ),
    ]
