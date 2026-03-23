from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('neuigkeiten/', views.neuigkeiten, name='neuigkeiten'),
    path('neuigkeiten/<slug:slug>/', views.neuigkeiten_detail, name='neuigkeiten_detail'),
    path('entdecken/', views.entdecken, name='entdecken'),
    path('oeffnungszeiten/', views.oeffnungszeiten, name='oeffnungszeiten'),
    path('preise/', views.preise, name='preise'),
    path('memberships/', views.memberships, name='memberships'),
    path('probemonat/', views.probemonat, name='probemonat'),
    path('mitgliedschaft/', views.mitgliedschaft, name='mitgliedschaft'),
    path('monatskarte/', views.monatskarte, name='monatskarte'),
    path('classes/', views.classes, name='classes'),
    path('kontakt/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
]
