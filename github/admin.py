from django.contrib import admin
from github.models import Project, Blob, Commit

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'github_repo',)
    list_filter   = ('created',)
    search_fields = ('title', 'description')
    
    actions = ['fetch_github']
    
    def fetch_github(self, request, queryset):
        updated = []
        for project in queryset:
            if project.fetch_github():
                updated.append(project.title)
        self.message_user(request, "%s successfully updated." % ', '.join(updated))
    fetch_github.short_description = 'Fetch from Github'

class CommitAdmin(admin.ModelAdmin):
    list_display = ('project', 'name', 'sha', 'created')
    list_filter = ('created',)
    actions = ['fetch_github', 'fetch_blobs']

    def fetch_github(self, request, queryset):
        fetched = []
        for commit in queryset:
            if commit.fetch_github():
                fetched.append(commit.sha)
        self.message_user(request, 'Successfully fetched %s' % (', '.join(fetched)))
    fetch_github.short_description = 'Fetch commit data'

    def fetch_blobs(self, request, queryset):
        fetched = []
        for commit in queryset:
            if commit.fetch_blobs():
                fetched.append(commit.sha)
        self.message_user(request, 'Successfully fetched blobs for %s' % (', '.join(fetched)))
    fetch_blobs.short_description = 'Fetch blobs for commits'

class BlobAdmin(admin.ModelAdmin):
    pass

admin.site.register(Project, ProjectAdmin)
admin.site.register(Commit, CommitAdmin)
admin.site.register(Blob, BlobAdmin)
