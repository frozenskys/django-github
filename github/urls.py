from django.conf.urls.defaults import *

urlpatterns = patterns('github.views',
    url(r'^$', 
        view='project_list', 
        name='project_index'
    ),
    url(r'^github-hook/(.+)/$',
        view='github_hook',
        name='project_github_hook'
    ),
    url(r'^([\w-]+)/$', 
        view='project_detail', 
        name='project_detail'
    ),
    url(r'^([\w-]+)/commits/$',
        view='commit_list',
        name='commit_list'
    ),
    url(r'^([\w-]+)/source/$',
        view='blob_list', 
        name='blob_list'
    ),
    url(r'^([\w-]+)/source/(.+)/download/$', 
        view='blob_download',
        name='blob_download'
    ),
    url(r'^([\w-]+)/source/(.+)', 
        view='blob_detail',
        name='blob_detail'
    ),
)
