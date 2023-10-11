# Generated by Django 4.2.5 on 2023-10-05 12:29

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('recipes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='shoppingcart',
            name='user',
            field=models.ForeignKey(help_text='Выберите пользователя, который добавил рецепт в корзину', on_delete=django.db.models.deletion.CASCADE, related_name='shopping_cart', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь'),
        ),
        migrations.AddField(
            model_name='recipe',
            name='author',
            field=models.ForeignKey(help_text='Выберите автора рецепта', on_delete=django.db.models.deletion.CASCADE, related_name='recipes', to=settings.AUTH_USER_MODEL, verbose_name='Автор рецепта'),
        ),
        migrations.AddField(
            model_name='recipe',
            name='ingredients',
            field=models.ManyToManyField(help_text='Выберите ингредиенты для рецепта и укажите их количество', related_name='recipes', through='recipes.AmountIngredient', to='recipes.ingredient', verbose_name='Ингридиенты'),
        ),
        migrations.AddField(
            model_name='recipe',
            name='tags',
            field=models.ManyToManyField(blank=True, help_text='Выберите теги для рецепта', related_name='recipes', to='recipes.tag', verbose_name='Тэги'),
        ),
        migrations.AddField(
            model_name='favorite',
            name='recipe',
            field=models.ForeignKey(help_text='Выберите рецепт, который был добавлен в избранное', on_delete=django.db.models.deletion.CASCADE, related_name='favorite', to='recipes.recipe', verbose_name='Рецепт'),
        ),
        migrations.AddField(
            model_name='favorite',
            name='user',
            field=models.ForeignKey(help_text='Выберите пользователя, который добавил рецепт в избранное', on_delete=django.db.models.deletion.CASCADE, related_name='favorite', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь'),
        ),
        migrations.AddField(
            model_name='amountingredient',
            name='ingredient',
            field=models.ForeignKey(help_text='Выберите ингредиент, который используется в рецепте', on_delete=django.db.models.deletion.CASCADE, to='recipes.ingredient', verbose_name='Ингредиент'),
        ),
        migrations.AddField(
            model_name='amountingredient',
            name='recipe',
            field=models.ForeignKey(help_text='Выберите рецепт, к которому относится ингредиент', on_delete=django.db.models.deletion.CASCADE, related_name='recipe_ingredient', to='recipes.recipe', verbose_name='Рецепт'),
        ),
        migrations.AddConstraint(
            model_name='shoppingcart',
            constraint=models.UniqueConstraint(fields=('user', 'recipe'), name='\nrecipes_shoppingcart recipe is cart alredy\n'),
        ),
        migrations.AddConstraint(
            model_name='recipe',
            constraint=models.CheckConstraint(check=models.Q(('name__length__gt', 0)), name='\nrecipes_recipe_name is empty\n'),
        ),
        migrations.AddConstraint(
            model_name='favorite',
            constraint=models.UniqueConstraint(fields=('recipe', 'user'), name='\nrecipes_favorite recipe is favorite alredy\n'),
        ),
    ]
