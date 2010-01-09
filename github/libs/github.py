try:
    import simplejson
except ImportError:
    import json as simplejson
import datetime
import httplib2
import re
import socket
import time
from urllib import urlencode, quote

class GithubAPI(object):
    """
    A simple library for interacting with Github's v2 api
    
    Supported methods:
    - get_user(username)
    - authenticate()
    - followers(username)
    - following(username)
    - watching(username)
    - get_repo(username, repo)
    - get_repos(username)
    - get_commits(username, repo, [branch])
    - get_commit(username, repo, sha)
    - get_tree(username, repo, sha)
    - get_blob(username, repo, sha, file_path)
    - create_gist(name, data, extension)
    - get_gist(gist_id)
    """
    _fetched = 0
    
    def __init__(self, username=None, token=None):
        self.username = username
        self.token = token
    
    def raw_api_call(self, url, parameters={}, http_method="GET", max_timeout=4):
        """
        Make an API Call to GitHub
        """
        # limit to 1 call per 1.15 seconds
        if time.time() - self._fetched <= 1.15:
            time.sleep(1.15 - (time.time() - self._fetched))
        self._fetched = time.time()
        
        sock = httplib2.Http(timeout=max_timeout)
        
        request_headers = { 'User-Agent': 'Python-httplib2' }
        
        parameters.update({ 'username': self.username,
                            'token': self.token })
        
        if http_method == 'POST':
            post_data = urlencode(parameters)
        elif parameters:
            url += '?%s' % urlencode(parameters)

        try:
            if http_method == 'POST':
                headers, response = sock.request(url, "POST", post_data, headers=request_headers)
            else:
                headers, response = sock.request(url)
        except socket.timeout:
            raise ValueError('Socket timed out')
                
        status = int(headers.pop('status', 200))
        if status != 200:
            raise ValueError('Returned status: %s' % (status))
        
        try:
            processed_response = simplejson.loads(response)
        except ValueError, e:
            raise ValueError('Error in data from GitHub API: %s' % e.message)
    
        return processed_response
    
    def process_user(self, json_data):
        return GithubAPIUser(json_data['user'])
    
    def process_users(self, json_data):
        return json_data['users']
       
    def process_repo_data(self, json_data):
        return GithubAPIRepo(json_data)
    
    def process_repo(self, json_data):
        return self.process_repo_data(json_data['repository'])
    
    def process_repos(self, json_data):
        return [self.process_repo_data(repo) for repo in json_data['repositories']]
    
    def process_commit_data(self, json_data):
        return GithubAPICommit(json_data)
    
    def process_commit(self, json_data):
        return self.process_commit_data(json_data['commit'])
    
    def process_commits(self, json_data):
        return [self.process_commit_data(commit) for commit in json_data['commits']]
    
    def process_tree_data(self, json_data):
        return [GithubAPIObject(obj) for obj in json_data['tree']]
    
    def process_blob_data(self, json_data):
        return GithubAPIBlob(json_data['blob'])
    
    def api_call(self, url, processor, http_method="GET", params={}, optional_params={}):
        """
        Thin wrapper for raw_api_call - fails silently
        """
        for (key, value) in optional_params.items():
            if not params.has_key(key):
                params[key] = value
        
        try:
            json_data = self.raw_api_call(url, parameters=params, http_method=http_method)
        except:
            return False
        
        return processor(json_data)
    
    def get_user(self, username, optional_params={}):
        return self.api_call(
            url='http://github.com/api/v2/json/user/show/%s' % (username),
            processor=self.process_user,
            optional_params=optional_params
        )
    
    def authenticate(self, optional_params={}):
        return self.get_user(self.username)
    
    def followers(self, username, optional_params={}):
        return self.api_call(
            url='http://github.com/api/v2/json/user/show/%s/followers' % (username),
            processor=self.process_users,
            optional_params=optional_params
        )
    
    def following(self, username, optional_params={}):
        return self.api_call(
            url='http://github.com/api/v2/json/user/show/%s/following' % (username),
            processor=self.process_users,
            optional_params=optional_params
        )
    
    def watching(self, username, optional_params={}):
        return self.api_call(
            url='http://github.com/api/v2/json/repos/watched/%s/' % (username),
            processor=self.process_repos,
            optional_params=optional_params
        )
    
    def get_repo(self, username, repo, optional_params={}):
        return self.api_call(
            url='http://github.com/api/v2/json/repos/show/%s/%s' % (username, repo),
            processor=self.process_repo,
            optional_params=optional_params
        )
    
    def get_repos(self, username, optional_params={}):
        return self.api_call(
            url='http://github.com/api/v2/json/repos/show/%s/' % (username),
            processor=self.process_repos,
            optional_params=optional_params
        )
    
    def get_commits(self, username, repo, branch='master', file_path=None, optional_params={}):
        url = 'http://github.com/api/v2/json/commits/list/%s/%s/%s' % (username, repo, branch)
        if file_path:
            url='%s/%s' % (url, file_path)
        return self.api_call(
            url=url,
            processor=self.process_commits,
            optional_params=optional_params
        )
    
    def get_commit(self, username, repo, sha, optional_params={}):
        return self.api_call(
            url='http://github.com/api/v2/json/commits/show/%s/%s/%s' % (username, repo, sha),
            processor=self.process_commit,
            optional_params=optional_params
        )
    
    def get_tree(self, username, repo, sha, optional_params={}):
        return self.api_call(
            url='http://github.com/api/v2/json/tree/show/%s/%s/%s' % (username, repo, sha),
            processor=self.process_tree_data,
            optional_params=optional_params
        )
    
    def get_blob(self, username, repo, sha, file_path, optional_params={}):
        return self.api_call(
            url='http://github.com/api/v2/json/blob/show/%s/%s/%s/%s' % (username, repo, sha, file_path),
            processor=self.process_blob_data,
            optional_params=optional_params
        )
    
    def create_gist(self, name, data, ext='.txt', optional_params={}, max_timeout=4):
        """
        This method needs improvement.  I've only been able to get it working
        by posting anonymously.  When I've added login & token to the post
        parameters, I get 401s.
        """
        url = 'http://gist.github.com/gists'
        sock = httplib2.Http(timeout=max_timeout)
        
        request_headers = { 'User-Agent': 'Python-httplib2' }
        
        parameters = { 'file_name[gistfile1]': name,
                       'file_contents[gistfile1]': data,
                       'file_ext[gistfile1]': ext }
        parameters.update(optional_params)
        
        qs = ''
        for key, value in parameters.items():
            qs += '%s=%s&' % (key, quote(value))

        try:
            headers, response = sock.request(url, "POST", qs, headers=request_headers)
        except socket.timeout:
            raise ValueError('Socket timed out')
        
        status = int(headers.pop('status', 200))
        if status != 302:
            raise ValueError('Returned status: %s' % (status))
        
        location = headers.pop('location')
        sock.request(location)
        
        matches = re.match('https?:\/\/gist\.github\.com\/(\d+)\/?', location)
        return matches.group(1)
    
    def get_gist(self, gist_id, max_timeout=4):
        url = 'http://gist.github.com/%s.txt' % (gist_id)
        sock = httplib2.Http(timeout=max_timeout)
        try:
            headers, response = sock.request(url)
        except socket.timeout:
            raise ValueError('Socket timed out')
        
        status = int(headers.pop('status', 200))
        if status != 200:
            raise ValueError('Returned status: %s' % (status))
        
        return response

def convert_github_timestamp(value):
    return datetime.datetime(*time.strptime(value[:-6], '%Y-%m-%dT%H:%M:%S')[:6])
        
class GenericAPIObject(object):
    pieces = []
    def __init__(self, data):
        for piece in self.pieces:
            setattr(self, piece, data.get(piece))

class GithubAPIUser(GenericAPIObject):
    pieces = ['id', 'login', 'name', 'company', 'location', 
              'email', 'blog', 'following_count', 'followers_count', 
              'public_gist_count', 'public_repo_count']

class GithubAPIRepo(GenericAPIObject):
    pieces = ['watchers', 'owner', 'name', 'description', 'private', 'url',
              'open_issues', 'fork', 'homepage', 'forks']

class GithubAPICommit(GenericAPIObject):
    pieces = ['message', 'parents', 'url', 'author', 'id', 'committed_date',
              'authored_date', 'tree', 'committer']
    def __init__(self, data):
        super(GithubAPICommit, self).__init__(data)
        self.committed_date = convert_github_timestamp(self.committed_date)
        self.authored_date = convert_github_timestamp(self.authored_date)

class GithubAPIObject(GenericAPIObject):
    pieces = ['name', 'sha', 'mode', 'type']

class GithubAPIBlob(GenericAPIObject):
    pieces = ['name', 'size', 'sha', 'mode', 'mime_type', 'data']
