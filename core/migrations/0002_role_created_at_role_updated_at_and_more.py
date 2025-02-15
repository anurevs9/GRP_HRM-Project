# Generated by Django 5.1.5 on 2025-02-15 05:48

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='role',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='role',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='recruitment',
            name='status',
            field=models.CharField(choices=[('OPEN', 'Open'), ('IN_PROGRESS', 'In Progress'), ('CLOSED', 'Closed')], default='open', max_length=20),
        ),
        migrations.AlterField(
            model_name='role',
            name='description',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='role',
            name='name',
            field=models.CharField(choices=[('ADMIN', 'Admin'), ('MANAGER', 'Manager'), ('TEAM_LEADER', 'Team Leader'), ('EMPLOYEE', 'Employee')], max_length=100),
        ),
    ]
