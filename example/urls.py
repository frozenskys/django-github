from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^projects/', include('github.urls')),
    (r'^admin/', include(admin.site.urls)),
)
