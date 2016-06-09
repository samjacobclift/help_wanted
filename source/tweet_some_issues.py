import os
from bs4 import BeautifulSoup
import tweepy
import requests

CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('ACCESS_TOKEN_SECRET')


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
        help_wanted_url += '?page=' + page

    res = requests.get(help_wanted_url)
    soup = BeautifulSoup(res.content, 'html.parser')
    issues = soup.findAll('div', class_='project')
    return [process_issue(i) for i in issues]


def tweet_issue(issue):
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

    api = tweepy.API(auth)
    api.update_status('here is an issue ' + issue['link'])

if __name__ == "__main__":
    # TODO tweet every hr
    # TODO remember whats been tweeted
        # redis or pickle?
    # TODO deploy to prod
    issues = scrap_issues()
    tweet_issue(issues[0])
