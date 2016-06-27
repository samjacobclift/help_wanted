import os

from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup
import tweepy
import requests

import logging
import redis

redis_conn = redis.from_url(os.environ.get("REDIS_URL", "localhost"))
logging.basicConfig()


CONSUMER_KEY = os.environ.get('TWITTER_CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('TWITTER_CONSUMER_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')

BLACKLIST = ['awesome-elixir']


class BlackListError(Exception):
    pass


def process_issue(issue):
    """
    Scrap the issue details out of
    issue html element
    """
    issue_links = issue.findAll('a')
    issue_link = issue_links[0]
    repo_url = issue_links[1]
    return {'link': issue_link.attrs['href'], 'repo': repo_url.attrs['href']}


def scrap_issues(page=None):
    """
    Scrap all the issues from a page
    of help wanted
    """
    help_wanted_url = 'https://libraries.io/help-wanted'

    # request a page if needed
    if page:
        help_wanted_url += '?page=' + str(page)

    res = requests.get(help_wanted_url)
    soup = BeautifulSoup(res.content, 'html.parser')
    issues = soup.findAll('div', class_='project')
    return [process_issue(i) for i in issues]


def get_repo_language(repo_link):
    """
    Get the repos language
    """
    repo_link = '/'.join(repo_link.split('/')[2:])
    return requests.get('https://api.github.com/repos/' + repo_link).json()['language']


def tweet_issue(issue):
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

    api = tweepy.API(auth)
    lang = get_repo_language(issue['repo'])

    in_black_list = any([item in issue['link'] for item in BLACKLIST])

    if not in_black_list:
        try:
            api.update_status('Take a look at this issue and help out open source ' + issue['link'] + ' #opensource #' + lang)
        except tweepy.error.TweepError:
            print('tweeting an existing tweet continuing')
    else:
        print('skipping as in black list ', issue)
        raise BlackListError()


def tweet_latest_issue():
    page_count = int(redis_conn.get('PAGE_COUNT'))
    issue_count = int(redis_conn.get('ISSUE_COUNT'))
    tweeting = True

    while tweeting:
        try:
            redis_conn.incr('ISSUE_COUNT')
            issues = scrap_issues(page_count)
            tweet_issue(issues[issue_count])
            tweeting = False

        except IndexError:
            redis_conn.set('ISSUE_COUNT', 0)
            redis_conn.incr('PAGE_COUNT')
        except BlackListError:
            continue

if __name__ == "__main__":
    if not redis_conn.get('ISSUE_COUNT'):
        redis_conn.set('ISSUE_COUNT', 1)
        redis_conn.set('PAGE_COUNT', 1)

    # tweet the first issues
    tweet_latest_issue()
    scheduler = BlockingScheduler()
    scheduler.add_job(tweet_latest_issue, 'interval', minutes=60)
    scheduler.start()
