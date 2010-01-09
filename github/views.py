from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.views.generic import list_detail
from github.models import Project, Blob

SECRET_KEY = getattr(settings, 'SECRET_KEY', '1337')

def project_list(request, paginate_by=20, **kwargs):
    return list_detail.object_list(
        request,
        queryset=Project.objects.all(),
        paginate_by=paginate_by,
        page=int(request.GET.get('page', 0)),
        **kwargs
    )

def project_detail(request, slug, **kwargs):
    return list_detail.object_detail(
        request,
        queryset=Project.objects.all(),
        slug=slug,
        slug_field='slug',
        template_object_name='project',
    )

def commit_list(request, slug, paginate_by=20, template_name='github/commit_list.html', **kwargs):
    project = get_object_or_404(Project, slug=slug)
    return list_detail.object_list(
        request,
        queryset=project.commits.all(),
        extra_context={'project': project},
        template_name=template_name,
        paginate_by=paginate_by,
        page=int(request.GET.get('page', 0)),
        **kwargs
    )

def blob_list(request, slug, template_name='github/blob_list.html', **kwargs):
    project = get_object_or_404(Project, slug=slug)
    latest_commit = project.get_latest_commit()
    if not latest_commit:
        raise Http404
    return list_detail.object_list(
        request,
        queryset=latest_commit.blobs.all(),
        extra_context={'project': project, 'commit': latest_commit},
        template_name=template_name,
        **kwargs
    )

def blob_detail(request, slug, path, template_name='github/blob_detail.html', **kwargs):
    project = get_object_or_404(Project, slug=slug)
    latest_commit = project.get_latest_commit()
    blob = get_object_or_404(latest_commit.blobs.all(), path=path)
    if not latest_commit:
        raise Http404
    return render_to_response(template_name, 
            { 'object': blob, 'project': project, 'commit': latest_commit }, 
            context_instance=RequestContext(request))

def blob_download(request, slug, path):
    project = get_object_or_404(Project, slug=slug)
    latest_commit = project.get_latest_commit()
    blob = get_object_or_404(latest_commit.blobs.all(), path=path)
    response = HttpResponse(blob.data, blob.mime_type)
    response['Content-Disposition'] = 'attachment; filename=%s' % (blob.name)
    return response

def github_hook(request, secret_key):
    if secret_key != SECRET_KEY:
        raise Http404
    if request.method == 'POST':
        try:
            data = simplejson.loads(request.POST)
            repo = data['repository']['name']
            project = Project.objects.get(github_repo=repo)
            project.fetch_github()
            return HttpResponse('OK')
        except:
            pass
    return HttpResponse('')
