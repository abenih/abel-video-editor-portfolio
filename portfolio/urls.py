from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'portfolio'

urlpatterns = [
    path('', views.home, name='home'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/upload/', views.upload_project, name='upload_project'),
    path('projects/<int:pk>/edit/', views.edit_project, name='edit_project'),
    path('projects/<int:pk>/delete/', views.delete_project, name='delete_project'),
    path('projects/manage/', views.manage_projects, name='manage_projects'),

    path('manage/profile/', views.manage_profile, name='manage_profile'),
    path('manage/skills/', views.manage_skills, name='manage_skills'),
    path('manage/skills/add/', views.manage_skill_add, name='manage_skill_add'),
    path('manage/skills/<int:pk>/edit/', views.manage_skill_edit, name='manage_skill_edit'),
    path('manage/skills/<int:pk>/delete/', views.manage_skill_delete, name='manage_skill_delete'),
    path('manage/<str:key>/', views.manage_content_list, name='manage_content_list'),
    path('manage/<str:key>/add/', views.manage_content_edit, name='manage_content_add'),
    path('manage/<str:key>/<int:pk>/edit/', views.manage_content_edit, name='manage_content_edit'),
    path('manage/<str:key>/<int:pk>/delete/', views.manage_content_delete, name='manage_content_delete'),

    path('login/', views.portfolio_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='portfolio:home'), name='logout'),
]
