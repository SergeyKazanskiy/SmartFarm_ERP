"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
# from django.urls import path

# urlpatterns = [
#     path('admin/', admin.site.urls),
# ]



from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# # Кастомные заголовки админки (локализация)
# admin.site.site_header = _("ERP Administration")
# admin.site.site_title = _("ERP")
# admin.site.index_title = _("Control Panel")

urlpatterns = [
#     # Админка с префиксом языка: /ru/admin/, /en/admin/
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),

#     # API v1
#     path("api/v1/", include("apps.companies.api.urls")),
#     path("api/v1/", include("apps.hr.api.urls")),
#     path("api/v1/", include("apps.tasks.api.urls")),
#     path("api/v1/", include("apps.cp.api.urls")),
# path("api/v1/", include("apps.procurement.api.urls")),

#     # OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Пример URL-адресов:
# http://localhost:8000/api/schema/ — YAML/JSON-схема.
# http://localhost:8000/api/docs/ — Swagger UI с кнопкой Authorize.