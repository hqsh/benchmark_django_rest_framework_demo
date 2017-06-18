"""benchmark_django_rest_framework_demo URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from benchmark_app.views import *

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^init_data/?$', InitDataView.as_view()),
    url(r'^company/(?P<pk>\d+)/?$', CompanyView.as_view()),
    url(r'^company/?$', CompanyView.as_view()),
    url(r'^department/(?P<pk>\d+)/?$', DepartmentView.as_view()),
    url(r'^department/?$', DepartmentView.as_view()),
    url(r'^employee/(?P<pk>\d+)/?$', EmployeeView.as_view()),
    url(r'^employee/?$', EmployeeView.as_view()),
    url(r'^project_team/(?P<pk>\d+)/?$', ProjectTeamView.as_view()),
    url(r'^project_team/?$', ProjectTeamView.as_view()),
    url(r'^pc/(?P<pk>\d+)/?$', PCView.as_view()),
    url(r'^pc/?$', PCView.as_view()),
    # url(r'^project_team_to_employee/(?P<pk>\d+)/?$', ProjectTeamToEmployeeView.as_view()),
    # url(r'^project_team_to_employee/?$', ProjectTeamToEmployeeView.as_view()),
]
