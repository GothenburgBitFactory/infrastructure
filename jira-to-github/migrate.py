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

JIRA_YEAR_START = 2008
JIRA_YEAR_END = 2018
JIRA_FILTER_TEMP = (
    'project={project} AND '
    'createdDate < {end}-01-01 AND '
    'createdDate >= {start}-01-01'
)


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

jira = JIRA(JIRA_URL, basic_auth=[JIRA_USERNAME, JIRA_PASSWORD])

print("Connection to JIRA successfully established.")
print("Fetching list of matching issues...")

# Get issue list for all the issues that match given project
issue_list = []
for year in range(JIRA_YEAR_START, JIRA_YEAR_END + 1):
    jira_filter = JIRA_FILTER_TEMP.format(project='TW', start=year, end=year+1)
    issue_list += jira.search_issues(jira_filter, maxResults=5000)

# Sort issue list
sorted_issue_list = list(sorted(
    issue_list,
    key=lambda i: int(i.key.split('-')[1])
))

print(f"The script will process {len(sorted_issue_list} matching issues now.")
