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


def tweet_issue(issue):
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

    api = tweepy.API(auth)
    print('tweeting ' + issue['link'])
    try:
        api.update_status('Take a look at this issue and help out open source ' + issue['link'])
    except tweepy.error.TweepError:
        print('tweeting an existing tweet continuing')


def tweet_latest_issue():
    page_count = int(redis_conn.get('PAGE_COUNT'))
    issue_count = int(redis_conn.get('ISSUE_COUNT'))

    try:
        redis_conn.incr('ISSUE_COUNT')
        issues = scrap_issues(page_count)
        tweet_issue(issues[issue_count])
    except IndexError:
        redis_conn.set('ISSUE_COUNT', 0)
        redis_conn.incr('PAGE_COUNT')

if __name__ == "__main__":
    if not redis_conn.get('ISSUE_COUNT'):
        redis_conn.set('ISSUE_COUNT', 1)
        redis_conn.set('PAGE_COUNT', 1)

    # tweet the first issues
    tweet_latest_issue()
    scheduler = BlockingScheduler()
    scheduler.add_job(tweet_latest_issue, 'interval', minutes=60)
    scheduler.start()
