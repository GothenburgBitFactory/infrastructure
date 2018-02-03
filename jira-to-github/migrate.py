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

GITHUB_URL_NEW_ISSUE = 'https://api.github.com/repos/{org}/{repo}/issues'
GITHUB_URL_NEW_COMMENT = 'https://api.github.com/repos/{org}/{repo}/issues/{issue}/comments'

JIRA_YEAR_START = 2008
JIRA_YEAR_END = 2018
JIRA_FILTER_TEMP = (
    'project={project} AND '
    'createdDate < {end}-01-01 AND '
    'createdDate >= {start}-01-01'
)

CLOSED_STATUSES = ('Resolved', 'Won\'t fix', 'Fixed')

def convert_timestamp(timestamp):
    """
    Converts timestamp from JIRA to GitHub preferred format.
    """

    return timestamp.split('.')[0] + 'Z'

def create_issue(repository_id, data, comments):
    """
    Create a issue in the GitHub repository.
    """

    org, repo = repository_id.split('/')

    session = requests.Session()
    session.auth = (GITHUB_USERNAME, GITHUB_PASSWORD)

    response = session.post(
        GITHUB_URL_NEW_ISSUE.format(org=org, repo=repo),
        json.dumps(data)
    )

    if response.status_code == 201:
        print(f'  Successfully created: {data["title"]}')
    else:
        print(f'  Could not create: {data["title"]}')
        print(f'  Response: {response.content}')
        return

    new_issue_id = json.loads(response.content)['number']
    for i, comment in enumerate(comments):
        print(GITHUB_URL_NEW_COMMENT.format(org=org, repo=repo, issue=new_issue_id))
        response = session.post(
            GITHUB_URL_NEW_COMMENT.format(org=org, repo=repo, issue=new_issue_id),
            json.dumps(comment)
        )
        if response.status_code == 201:
            print(f'    Successfully created comment {i}')
        else:
            print(f'    Could not create comment {i}')
            print(f'    Response: {response.content}')

def generate_issue_data(issue):
    """
    Generates a issue data dict for given identifier.
    """

    data = {
        'title': f"[{issue.key}] {issue.fields.summary}",
        'body': f"{issue.fields.description}",
        'created_at': convert_timestamp(issue.fields.created),
        'updated_at': convert_timestamp(issue.fields.updated),
        'closed': issue.fields.status.name in CLOSED_STATUSES
    }

    comments = []
    for comment in issue.fields.comment.comments:
        comments.append({
            'body': comment.body,
            'created_at': convert_timestamp(comment.created),
        })

    return data, comments

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
