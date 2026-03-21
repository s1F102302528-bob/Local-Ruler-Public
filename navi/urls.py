from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('data/', views.data, name='data'),
    path('cases/', views.cases, name='cases'),
    path('learning/', views.learning, name='learning'),
    path('settings/', views.settings, name='settings'),
    path('analysis/<int:region_id>/', views.analysis, name='analysis'),
    path('similar/<int:region_id>/', views.similar, name='similar'),
    path('heatmap/<int:region_id>/', views.heatmap, name='heatmap'),
    path('api/heatmap/<int:region_id>/', views.heatmap_api, name='heatmap_api'),
    path('api/map-data/', views.api_map_data, name='api_map_data'),
    path('api/municipality/<str:city_code>/', views.api_municipality_data, name='api_municipality_data'),
    path("maps/", views.maps_view, name="maps"),

]