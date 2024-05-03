import http

from django.db.models import Sum
from django.http import HttpResponse
from djoser.views import UserViewSet
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import Subscription
from .paginators import UsersAndRecipeListAPIPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (User, Tag,
                          TagSerializer, Ingredient, IngredientSerializer,
                          Recipe, ShoppingCart,
                          ShoppingCartAndFavoritesSerializer,
                          RecipeIngredient, Favorite, SubscriptionSerializer,
                          RecipeSerializer, CreateRecipeSerializer)
from .utils import RecipeManager


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by('-id')
    pagination_class = UsersAndRecipeListAPIPagination

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthorOrReadOnly]
        elif self.action in ['create', 'download_shopping_cart']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateRecipeSerializer
        elif self.action == 'download_shopping_cart':
            return ShoppingCartAndFavoritesSerializer
        return RecipeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != 'list':
            return queryset

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

    @action(methods=['get'], detail=False)
    def download_shopping_cart(self, request, pk=None, *args, **kwargs):
        user = request.user
        try:
            shopping_cart = ShoppingCart.objects.get(user=user)
        except ShoppingCart.DoesNotExist:
            return Response({'error': 'Корзина покупок не найдена.'},
                            status=http.HTTPStatus.NOT_FOUND)

        recipes = shopping_cart.recipes.all()
        if not recipes.exists():
            return Response({'error': 'Ваша корзина пуста.'},
                            status=http.HTTPStatus.OK)

        ingredients = RecipeIngredient.objects.filter(
            recipe__in=recipes).values(
            'ingredient__name', 'ingredient__measurement_unit').annotate(
            total_amount=Sum('amount')).order_by('ingredient__name')

        shopping_list = "\r\n".join([
            (f"{item['ingredient__name']} "
             f"({item['ingredient__measurement_unit']}) — "
             f"{item['total_amount']}")
            for item in ingredients
        ])

        response = HttpResponse(shopping_list,
                                content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"')
        return response


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
        return RecipeManager.add_recipe_to_collection(
            user=request.user,
            recipe_id=recipe_id,
            collection_model=ShoppingCart,
            serializer_class=ShoppingCartAndFavoritesSerializer,
            request=request
        )

    def delete(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        return RecipeManager.remove_recipe_from_collection(
            user=request.user,
            recipe_id=recipe_id,
            collection_model=ShoppingCart
        )


class FavoriteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        return RecipeManager.add_recipe_to_collection(
            user=request.user,
            recipe_id=recipe_id,
            collection_model=Favorite,
            serializer_class=ShoppingCartAndFavoritesSerializer,
            request=request
        )

    def delete(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        return RecipeManager.remove_recipe_from_collection(
            user=request.user,
            recipe_id=recipe_id,
            collection_model=Favorite
        )


class SubscriptionsListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionSerializer
    pagination_class = UsersAndRecipeListAPIPagination

    def get_queryset(self):
        try:
            return Subscription.objects.get(
                user=self.request.user).subscription.all()
        except Subscription.DoesNotExist:
            return []


class SubscriptionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        author_id = kwargs.get('pk')
        user = request.user

        try:
            author = User.objects.get(pk=author_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден.'},
                            status=http.HTTPStatus.NOT_FOUND)

        if author == user:
            return Response(
                {'error': 'Нельзя подписаться на самого себя.'},
                status=http.HTTPStatus.BAD_REQUEST)

        subscription, created = Subscription.objects.get_or_create(user=user)

        if not subscription.subscription.filter(pk=author_id).exists():
            subscription.subscription.add(author)
            serializer = SubscriptionSerializer(
                author, context={'request': request})
            return Response(serializer.data, status=http.HTTPStatus.CREATED)

        return Response(
            {'error': 'Вы уже подписаны на этого пользователя.'},
            status=http.HTTPStatus.BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        author_id = kwargs.get('pk')
        user = request.user

        try:
            author = User.objects.get(pk=author_id)
            subscription = Subscription.objects.get(user=user)
        except (User.DoesNotExist, Subscription.DoesNotExist):
            return Response(
                {'error': 'Пользователь или подписка не найдены.'},
                status=http.HTTPStatus.NOT_FOUND)

        if subscription.subscription.filter(pk=author_id).exists():
            subscription.subscription.remove(author)
            return Response(
                {'success': 'Успешно отписались от пользователя..'},
                status=http.HTTPStatus.NO_CONTENT)

        return Response(
            {'error': 'Вы не подписаны на данного пользователя.'},
            status=http.HTTPStatus.BAD_REQUEST)
