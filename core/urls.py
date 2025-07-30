from django.conf import settings
from django.urls import include, path
from django.contrib import admin

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views
from core.test_views import (
    test_404, test_500, test_403, test_400, test_401, test_502, test_503, test_index,
    preview_404, preview_400, preview_401, preview_403, preview_500, preview_502, preview_503
)

urlpatterns = [
    path("", include('apps.main.urls')),
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path('lists/', include('apps.mailer.urls')),
    path('templates/', include('apps.mail_templates.urls')),
    path('emails/', include('apps.emails.urls')),
    path('campaigns/', include('apps.campaigns.urls')),
    path('accounts/', include('apps.accounts.urls')), 
    path('dashboard/', include('apps.dashboard.urls')),
    path('moderation/', include('apps.moderation.urls')),
    path('billing/', include('apps.billing.urls')),
    path('support/', include('apps.support.urls')),
    
    # Test URLs for error pages (remove in production)
    path('test/', test_index, name='test_index'),
    path('test/404/', test_404, name='test_404'),
    path('test/500/', test_500, name='test_500'),
    path('test/403/', test_403, name='test_403'),
    path('test/400/', test_400, name='test_400'),
    path('test/401/', test_401, name='test_401'),
    path('test/502/', test_502, name='test_502'),
    path('test/503/', test_503, name='test_503'),
    
    # Preview URLs (без HTTP статуса ошибки)
    path('preview/404/', preview_404, name='preview_404'),
    path('preview/400/', preview_400, name='preview_400'),
    path('preview/401/', preview_401, name='preview_401'),
    path('preview/403/', preview_403, name='preview_403'),
    path('preview/500/', preview_500, name='preview_500'),
    path('preview/502/', preview_502, name='preview_502'),
    path('preview/503/', preview_503, name='preview_503'),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    # path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]
