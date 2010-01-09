import logging
import time
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option

from github.models import Project

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--all', action='store_true', dest='fetch_all', default=False,
            help='Fetch and process all repos.'),
        make_option('--verbose', action='store_true', dest='verbose', default=False,
            help='Verbose output.'),
    )
    help = "Fetch and process GitHub projects, downloading commits and blobs for the latest commit."
    args = '[repo name]'

    def handle(self, repo_name='', *args, **options):
        fetch_all = options.get('fetch_all', False)
        verbose = options.get('verbose', False)
        
        if not repo_name and not fetch_all:
            raise CommandError('Usage is fetch_github %s' % self.args)
        elif repo_name:
            qs = Project.objects.filter(github_repo=repo_name.strip())
        else:
            qs = Project.objects.all()
        
        logging.basicConfig(
            filename='github_log.log',
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)-8s %(message)s',
        )
        
        if verbose:
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
            console.setFormatter(formatter)
            logging.getLogger('').addHandler(console)

        logging.info('Download starting, fetching %d repos' % qs.count())
        total_start = time.time()
        
        for project in qs:
            start = time.time()
            logging.info("Processing: %s..." % project.title)
            commits_processed = project.fetch_github()
            end = time.time()
            logging.info("%d new commits processed (took %fs)" % (len(commits_processed), end - start))
            
        total_end = time.time()
        logging.info("Finished processing %d repos" % qs.count())
        logging.info("Took %f seconds" % (total_end - total_start))
