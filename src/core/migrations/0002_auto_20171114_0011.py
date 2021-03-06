# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-14 05:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scene',
            name='name',
            field=models.CharField(help_text='Display name of the scene.', max_length=128),
        ),
        migrations.AlterField(
            model_name='scene',
            name='slug',
            field=models.SlugField(help_text='Unique name of the scene.', unique=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='auto_managed',
            field=models.BooleanField(default=True, help_text='If this unit can be controlled by other tasks.'),
        ),
        migrations.AlterField(
            model_name='unit',
            name='dimmable',
            field=models.BooleanField(default=False, help_text='Whether or not the unit can be dimmed.'),
        ),
        migrations.AlterField(
            model_name='unit',
            name='house',
            field=models.CharField(choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E'), ('F', 'F'), ('G', 'G'), ('H', 'H'), ('I', 'I'), ('J', 'J'), ('K', 'K'), ('L', 'L'), ('M', 'M'), ('N', 'N'), ('O', 'O'), ('P', 'P')], default='M', help_text='X10 house code.', max_length=1),
        ),
        migrations.AlterField(
            model_name='unit',
            name='name',
            field=models.CharField(help_text='Display name of the unit.', max_length=128),
        ),
        migrations.AlterField(
            model_name='unit',
            name='number',
            field=models.PositiveSmallIntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16')], help_text='X10 unit number.'),
        ),
        migrations.AlterField(
            model_name='unit',
            name='slug',
            field=models.SlugField(help_text='Unique name of the unit.', unique=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='state',
            field=models.BooleanField(default=False, help_text='If the unit is on or off.'),
        ),
    ]
