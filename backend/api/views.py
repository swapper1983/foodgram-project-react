from collections import defaultdict

from django.http import Http404, HttpResponse  # , JsonResponse
# from .serializers import *
from recipes.models import Subscriptions
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (ChangePasswordSerializer, CreateRecipeSerializer,
                          Favorites, Ingredient, IngredientSerializer,
                          LoginSerializer, Recipe, RecipeIngredient,
                          RecipeSerializer, RegistrationSerializer,
                          ShoppingCart, ShoppingCartAndFavoritesSerializer,
                          SubscriptionSerializer, Tag, TagSerializer, User,
                          UserSerializer)


class UsersDispatcherAPIView(APIView):

    def post(self, request, *args, **kwargs):
        view = RegistrationAPIView.as_view()
        django_request = request._request
        return view(django_request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        view = UsersListAPI.as_view()
        django_request = request._request
        return view(django_request, *args, **kwargs)


class RegistrationAPIView(APIView):
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data,
                                            context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = {
            "email": user.email,
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
        return Response(data, status=201)


class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data,
                                     context={'request': request})

        serializer.is_valid(raise_exception=True)
        token = serializer.save()
        return Response({'auth_token': token.key})


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated, ]

    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=204)


class UserProfileAPIView(APIView):
    def get_permissions(self):
        if self.kwargs['pk'] == 'me':
            self.permission_classes = [IsAuthenticated, ]
        else:
            self.permission_classes = [AllowAny, ]
        return super(UserProfileAPIView, self).get_permissions()

    def get_object(self, pk):
        if pk == "me":
            return self.request.user
        if pk.isdigit():
            try:
                return User.objects.get(pk=pk)
            except User.DoesNotExist:
                raise Http404
        else:
            raise Http404

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        user = self.get_object(pk)
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data,
                                              context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(status=204)
        return Response(serializer.errors, status=400)


class UsersAndRecipeListAPIPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100


class UsersListAPI(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = UsersAndRecipeListAPIPagination


class TagsListAPI(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class TagAPIView(generics.RetrieveAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientsListAPI(generics.ListAPIView):
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        name = self.request.query_params.get('name')
        if name:
            queryset = Ingredient.objects.filter(name__startswith=name)
            return queryset
        else:
            return Ingredient.objects.all()


class IngredientAPIView(generics.RetrieveAPIView):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class RecipeDispatcherAPIView(APIView):

    def post(self, request, *args, **kwargs):
        view = CreateRecipeAPIView.as_view()
        django_request = request._request
        return view(django_request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        view = RecipeListAPIView.as_view()
        django_request = request._request
        return view(django_request, *args, **kwargs)


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
        print(shopping_list)

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

        favorites, created = Favorites.objects.get_or_create(user=user)

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
            favorites = Favorites.objects.get(user=user)
        except (Recipe.DoesNotExist, Favorites.DoesNotExist):
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


class RecipeByIDDispatcherAPIView(APIView):

    def get(self, request, *args, **kwargs):
        view = RecipeRetrieveAPIView.as_view()
        django_request = request._request
        return view(django_request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        view = RecipeUpdateAndDestroyAPIView.as_view()
        django_request = request._request
        return view(django_request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        view = RecipeUpdateAndDestroyAPIView.as_view()
        django_request = request._request
        return view(django_request, *args, **kwargs)


class RecipeRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = UsersAndRecipeListAPIPagination


class RecipeUpdateAndDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = CreateRecipeSerializer
    pagination_class = UsersAndRecipeListAPIPagination

    def delete(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            recipe = Recipe.objects.get(pk=pk)
        except Recipe.DoesNotExist:
            return Response({'error': 'Рецепт не найден.'}, status=404)
        if recipe.author != request.user:
            return Response(
                {'error': 'Вы не являетесь автором данного рецепта.'},
                status=403)
        return super().delete(request, *args, **kwargs)


class CreateRecipeAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateRecipeSerializer
    pagination_class = UsersAndRecipeListAPIPagination
