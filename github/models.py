import os
import time

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.template.defaultfilters import slugify
from github.libs.github import GithubAPI

GITHUB_LOGIN = getattr(settings, 'GITHUB_LOGIN', 'coleifer')
GITHUB_TOKEN = getattr(settings, 'GITHUB_TOKEN', '')
github_client = GithubAPI(GITHUB_LOGIN, GITHUB_TOKEN)

class Project(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, editable=False)
    description = models.TextField()
    github_repo = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ('title',)
    
    def __unicode__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(Project, self).save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('project_detail', args=[self.slug])
    
    def get_latest_commit(self):
        try:
            return self.commits.all()[0]
        except IndexError:
            return None
    
    @property
    def github_url(self):
        if not GITHUB_LOGIN or not self.github_repo:
            return ''
        return 'http://github.com/%s/%s' % (GITHUB_LOGIN, self.github_repo)
    
    @property
    def github_clone_command(self):
        if not GITHUB_LOGIN or not self.github_repo:
            return ''
        return 'git clone git://github.com/%s/%s.git' % (GITHUB_LOGIN, self.github_repo)
    
    def fetch_github(self):
        if not self.github_repo:
            raise AttributeError("No GitHub repo associated with project model")
        
        commits_processed = []
        
        commit_list = github_client.get_commits(GITHUB_LOGIN, self.github_repo)
        if not commit_list:
            return commits_processed
        
        # store all the commits - an API call can be saved here, as all the
        # necessary commit data is returned by the get_commits() call.
        for commit in commit_list:
            instance, created = Commit.objects.get_or_create(project=self, sha=commit.id)
            if created:
                instance.created = commit.committed_date
                instance.message = commit.message
                instance.name = commit.committer.get('name', '')
                instance.tree = commit.tree
                instance.url = commit.url
                instance.project = self
                instance.save()
                commits_processed.append(instance)
        
        # download the *latest* tree if new commits exist
        if len(commits_processed):        
            commit = commits_processed[0]
            commit.fetch_blobs()
        
        return commits_processed
    
class Commit(models.Model):
    project = models.ForeignKey(Project, related_name='commits')
    sha = models.CharField(max_length=255)
    tree = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    url = models.URLField()
    
    class Meta:
        ordering = ['-created']
    
    def __unicode__(self):
        return '%s: %s' % (self.project.title, self.message)
    
    def get_absolute_url(self):
        return self.url
    
    def fetch_github(self):
        if not self.project or not self.project.github_repo:
            raise AttributeError('Required attribute missing: "github_repo" on %s' % self.project)
        commit = github_client.get_commit(GITHUB_LOGIN, self.project.github_repo, self.sha)
        if commit:
            self.tree = commit.tree
            self.created = commit.committed_date
            self.name = commit.committer.get('name', '')
            self.message = commit.message
            self.url = commit.url
            self.save()
        return commit
    
    def fetch_blobs(self):
        def process_tree(tree, path=''):
            objs = github_client.get_tree(GITHUB_LOGIN, self.project.github_repo, tree)
            for obj in objs:
                if obj.type == 'tree':
                    process_tree(obj.sha, path + obj.name + '/')
                blob, created = Blob.objects.get_or_create(commit=self, name=obj.name, path='%s%s' % (path, obj.name))
                if created:
                    fetched = blob.fetch_github(tree, path)
            return
        process_tree(self.tree)

class Blob(models.Model):
    commit = models.ForeignKey(Commit, related_name='blobs')
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=255, editable=False)
    size = models.IntegerField(default=0)
    mime_type = models.CharField(max_length=255)
    data = models.TextField()
    sha = models.CharField(max_length=255)
    
    class Meta:
        ordering = ['-commit__created', 'commit__project__title', 'path']
    
    def __unicode__(self):
        return '%s (%s)' % (self.path, self.size)
    
    def get_absolute_url(self):
        return reverse('blob_detail', args=[self.commit.project.slug, self.path])
    
    @property
    def download_url(self):
        return reverse('blob_download', args=[self.commit.project.slug, self.path])
    
    def fetch_github(self, tree, path=''):
        if not self.commit or not self.name:
            raise AttributeError('Required attribute missing on Blob object')
        blob = github_client.get_blob(GITHUB_LOGIN, self.commit.project.github_repo, tree, self.name)
        if blob:
            self.path = path + blob.name
            self.size = blob.size
            self.mime_type = blob.mime_type
            self.data = blob.data
            self.sha = blob.sha
            self.save()
        return blob
