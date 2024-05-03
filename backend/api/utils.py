import http

from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response

from recipes.models import Recipe


class RecipeManager:

    @staticmethod
    def validate_image(value):
        if not value:
            raise serializers.ValidationError(
                "Поле image не может быть пустым.")
        return value

    @staticmethod
    def add_recipe_to_collection(user,
                                 recipe_id,
                                 collection_model,
                                 serializer_class,
                                 request):
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({'error': 'Рецепт не найден.'},
                            status=http.HTTPStatus.BAD_REQUEST)
        collection, created = collection_model.objects.get_or_create(user=user)

        if not collection.recipes.filter(pk=recipe_id).exists():
            collection.recipes.add(recipe)
            serializer = serializer_class(recipe, context={'request': request})
            return Response(serializer.data, status=http.HTTPStatus.CREATED)

        return Response(
            {'error': 'Рецепт уже добавлен в избранное/корзину.'},
            status=http.HTTPStatus.BAD_REQUEST)

    @staticmethod
    def remove_recipe_from_collection(user, recipe_id, collection_model):

        recipe = get_object_or_404(Recipe, pk=recipe_id)
        collection = get_object_or_404(collection_model, user=user)

        if collection.recipes.filter(pk=recipe_id).exists():
            collection.recipes.remove(recipe)
            return Response(
                {'success': 'Рецепт удалён из избранного/корзины.'},
                status=http.HTTPStatus.NO_CONTENT)

        return Response(
            {'error': 'Рецепт не найден в избранном/корзине.'},
            status=http.HTTPStatus.BAD_REQUEST)
