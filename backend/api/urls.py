from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views import RecipeViewSet, UsersViewSet, TagsViewSet, IngredientsViewSet

router = DefaultRouter()
router.register(r'users', UsersViewSet, basename='users')
router.register(r'recipes', RecipeViewSet, basename='recipes')
router.register(r'tags', TagsViewSet, basename='tags')
router.register(r'ingredients', IngredientsViewSet, basename='ingredients')

urlpatterns = [
    path('users/<int:pk>/subscribe/',
         views.SubscriptionsAPIView.as_view(), name='subscription_add'),
    path('users/subscriptions/',
         views.SubscriptionsListAPIView.as_view(), name='subscriptions_list'),
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
    path('recipes/<int:pk>/shopping_cart/',
         views.ShoppingCartAPIView.as_view(),
         name='add_to_shopping_cart'),
    path('recipes/<int:pk>/favorite/',
         views.FavoriteAPIView.as_view(),
         name='add_to_favorite'),
]
