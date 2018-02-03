"""
Usage: migrate.py <filter> <github_repo>

Options:
    <filter>          The filter for issues to be migrated.
    <github_repo>     The github repo name in the 'GothenburgBitFactory/infrastructure' format
"""

import docopt
import json
import requests

from jira import JIRA

from config import (
    JIRA_USERNAME,
    JIRA_PASSWORD,
    JIRA_URL,
    GITHUB_USERNAME,
    GITHUB_PASSWORD
)

GITHUB_URL = 'https://api.github.com/repos/{org}/{repo}/issues'

jira = JIRA(JIRA_URL, basic_auth=[JIRA_USERNAME, JIRA_PASSWORD])


def create_issue(repository_id, issue_data, comments):
    org, repo = repository_id.split('/')

    session = requests.Session()
    session.auth = (GITHUB_USERNAME, GITHUB_PASSWORD)

    issue = {
        'title': issue_data['title'],
        'body': issue_data['body'],
        'labels': issue_data.get('labels') or []
    }

    response = session.post(
        GITHUB_URL.format(org=org, repo=repo),
        json.dumps(issue)
    )

    if response.status_code == 201:
        print ('Successfully created Issue {0:s}'.format(issue['title']))
    else:
        print ('Could not create Issue {0:s}'.format(issue['title']))
        print ('Response:', response.content)

test_issue = {
    'title': 'Imported issue',
    'body': 'This is body of the issue',
    'labels': ['bug']
}

create_issue('tbabej/testimport', test_issue, [])
