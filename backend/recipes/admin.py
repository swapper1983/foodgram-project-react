from django.contrib import admin

from .models import (Favorites, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Subscriptions, Tag)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = [RecipeIngredientInline, ]
    list_display = ('name', 'author_name', 'cooking_time', 'favorites_count')
    search_fields = ['name', 'text', 'author__username']
    list_filter = ('tags', 'author')

    def author_name(self, obj):
        return obj.author.first_name + ' ' + obj.author.last_name
    author_name.short_description = 'Имя и фамилия автора'

    def favorites_count(self, obj):
        return Favorites.objects.filter(recipes=obj).count()
    favorites_count.short_description = 'Добавлений в избранное'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug')
    search_fields = ['name']


@admin.register(Favorites)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'list_recipes')
    search_fields = ['user__username', 'recipe__name']

    def list_recipes(self, obj):
        return ", ".join([recipe.name for recipe in obj.recipes.all()])

    list_recipes.short_description = 'Recipes'


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'list_recipes')
    search_fields = ['user__username', 'recipe__name']

    def list_recipes(self, obj):
        return ", ".join([recipe.name for recipe in obj.recipes.all()])

    list_recipes.short_description = 'Recipes'


@admin.register(Subscriptions)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'list_subscriptions')
    search_fields = ['user__username', 'subscription__username']

    def list_subscriptions(self, obj):
        return ", ".join([user.username for user in obj.subscription.all()])

    list_subscriptions.short_description = 'Subscriptions'
