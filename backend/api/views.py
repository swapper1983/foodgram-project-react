from collections import defaultdict

from django.http import HttpResponse
from djoser.views import UserViewSet
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import Subscriptions
from .serializers import User, Tag, \
    TagSerializer, Ingredient, IngredientSerializer, Recipe, ShoppingCart, \
    ShoppingCartAndFavoritesSerializer, RecipeIngredient, Favorite, \
    SubscriptionSerializer, RecipeSerializer, CreateRecipeSerializer


class UsersAndRecipeListAPIPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100


class RecipeViewSet(viewsets.ViewSet):

    def create(self, request, *args, **kwargs):
        view = CreateRecipeAPIView.as_view()
        return view(request._request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        view = RecipeListAPIView.as_view()
        return view(request._request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        view = RecipeRetrieveAPIView.as_view()
        return view(request._request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        view = RecipeUpdateAndDestroyAPIView.as_view()
        return view(request._request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        view = RecipeUpdateAndDestroyAPIView.as_view()
        return view(request._request, *args, **kwargs)

    @action(methods=['get'], detail=False)
    def download_shopping_cart(self, request, pk=None, *args, **kwargs):
        view = DownloadShoppingCartAPIView.as_view()
        return view(request._request, *args, **kwargs)


class UsersViewSet(UserViewSet):
    pagination_class = UsersAndRecipeListAPIPagination

    def get_permissions(self):
        if self.action == 'me':
            self.permission_classes = [IsAuthenticated, ]
        else:
            self.permission_classes = [AllowAny, ]
        return super().get_permissions()


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', None)
        if name is not None:
            queryset = queryset.filter(name__startswith=name)
        return queryset


class ShoppingCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        user = request.user

        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({'error': 'Рецепт не найден.'}, status=400)

        shopping_cart, created = ShoppingCart.objects.get_or_create(user=user)

        if not shopping_cart.recipes.filter(pk=recipe_id).exists():
            shopping_cart.recipes.add(recipe)
            serializer = (ShoppingCartAndFavoritesSerializer(
                recipe, context={'request': request}))
            return Response(serializer.data, status=201)
        else:
            return Response(
                {'error': 'Рецепт уже находится в корзине покупок.'},
                status=400)

    def delete(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        user = request.user

        try:
            recipe = Recipe.objects.get(pk=recipe_id)
            shopping_cart = ShoppingCart.objects.get(user=user)
        except (Recipe.DoesNotExist, ShoppingCart.DoesNotExist):
            return Response(
                {'error': 'Рецепт или корзина покупок не найдена.'},
                status=404)

        if shopping_cart.recipes.filter(pk=recipe_id).exists():
            shopping_cart.recipes.remove(recipe)
            return Response(
                {'success': 'Рецепт удален из корзины покупок.'},
                status=204)
        else:
            return Response(
                {'error': 'Рецепт не найден в корзине покупок.'},
                status=400)


class DownloadShoppingCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        shopping_cart = ShoppingCart.objects.get(user=user)
        if shopping_cart.recipes.count() == 0:
            return Response({'error': 'Ваша корзина пуста.'}, status=200)

        ingredients_summary = defaultdict(int)
        for recipe in shopping_cart.recipes.all():
            for ingredient in RecipeIngredient.objects.filter(recipe=recipe):
                ingredients_summary[
                    f'{ingredient.ingredient.name} '
                    f'({ingredient.ingredient.measurement_unit})'] += int(
                    ingredient.amount)

        shopping_list = (
            "\r\n".join([f"{name} — {amount}" for name, amount
                         in ingredients_summary.items()]))

        response = HttpResponse(shopping_list,
                                content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"')
        return response


class FavoriteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        user = request.user

        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({'error': 'Рецепт не найден.'}, status=400)

        favorites, created = Favorite.objects.get_or_create(user=user)

        if not favorites.recipes.filter(pk=recipe_id).exists():
            favorites.recipes.add(recipe)
            serializer = ShoppingCartAndFavoritesSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=201)
        else:
            return Response(
                {'error': 'Рецепт уже находится в корзине покупок.'},
                status=400)

    def delete(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        user = request.user

        try:
            recipe = Recipe.objects.get(pk=recipe_id)
            favorites = Favorite.objects.get(user=user)
        except (Recipe.DoesNotExist, Favorite.DoesNotExist):
            return Response(
                {'error': 'Рецепт или корзина покупок не найдена.'},
                status=404)

        if favorites.recipes.filter(pk=recipe_id).exists():
            favorites.recipes.remove(recipe)
            return Response(
                {'success': 'Рецепт удален из корзины покупок.'},
                status=204)
        else:
            return Response(
                {'error': 'Рецепт не найден в корзине покупок.'},
                status=400)


class SubscriptionsListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionSerializer
    pagination_class = UsersAndRecipeListAPIPagination

    def get_queryset(self):
        queryset = Subscriptions.objects.get_subscriptions(
            user=self.request.user)
        return queryset


class SubscriptionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        author_id = kwargs.get('pk')
        user = request.user

        try:
            author = User.objects.get(pk=author_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден.'}, status=404)

        if author == user:
            return Response(
                {'error': 'Нельзя подписаться на самого себя.'},
                status=400)

        subscription, created = Subscriptions.objects.get_or_create(user=user)

        if not subscription.subscription.filter(pk=author_id).exists():
            subscription.subscription.add(author)
            serializer = SubscriptionSerializer(
                author, context={'request': request})
            return Response(serializer.data, status=201)
        else:
            return Response(
                {'error': 'Вы уже подписаны на этого пользователя.'},
                status=400)

    def delete(self, request, *args, **kwargs):
        author_id = kwargs.get('pk')
        user = request.user

        try:
            author = User.objects.get(pk=author_id)
            subscription = Subscriptions.objects.get(user=user)
        except (User.DoesNotExist, Subscriptions.DoesNotExist):
            return Response(
                {'error': 'Пользователь или подписка не найдены.'},
                status=404)

        if subscription.subscription.filter(pk=author_id).exists():
            subscription.subscription.remove(author)
            return Response(
                {'success': 'Успешно отписались от пользователя..'},
                status=204)
        else:
            return Response(
                {'error': 'Вы не подписаны на данного пользователя.'},
                status=400)


class RecipeListAPIView(generics.ListAPIView):
    serializer_class = RecipeSerializer
    pagination_class = UsersAndRecipeListAPIPagination

    def get_queryset(self):
        queryset = Recipe.objects.all().order_by('-id')
        is_favorited = self.request.query_params.get('is_favorited')
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart')
        author_id = self.request.query_params.get('author')
        tags = self.request.query_params.getlist('tags')
        if self.request.user.is_authenticated:

            if is_favorited:
                queryset = queryset.filter(favorite_by__user=self.request.user)

            if is_in_shopping_cart:
                queryset = queryset.filter(
                    in_shopping_carts__user=self.request.user)

        if author_id:
            if author_id == 'me':
                queryset = queryset.filter(author=self.request.user)
            else:
                queryset = queryset.filter(author_id=author_id)

        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()

        return queryset


class RecipeRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = UsersAndRecipeListAPIPagination


class RecipeUpdateAndDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = CreateRecipeSerializer
    pagination_class = UsersAndRecipeListAPIPagination

    def check_object_permissions(self, request, obj):
        if obj.author != request.user:
            raise PermissionDenied(
                "Вы не можете редактировать или удалять этот рецепт.")

    def delete(self, request, *args, **kwargs):
        recipe = self.get_object()
        self.check_object_permissions(request, recipe)
        return super().delete(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        recipe = self.get_object()
        self.check_object_permissions(request, recipe)
        return super().update(request, *args, **kwargs)


class CreateRecipeAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateRecipeSerializer
    pagination_class = UsersAndRecipeListAPIPagination
