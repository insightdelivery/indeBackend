from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SysCodeManagerViewSet

router = DefaultRouter()
router.register(r'syscode', SysCodeManagerViewSet, basename='syscode')

app_name = 'systemManage'

urlpatterns = [
    path('', include(router.urls)),
]



