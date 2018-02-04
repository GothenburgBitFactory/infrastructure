#!/usr/bin/python3

"""
Usage: migrate.py <project> <repo>

Options:
    <project>         The project whose issues are to be migrated.
    <repo>            The github repo name in the 'GothenburgBitFactory/infrastructure' format
"""

import json
import requests
import time
import os
import docopt

from jira import JIRA

from config import (
    JIRA_USERNAME,
    JIRA_PASSWORD,
    JIRA_URL,
    GITHUB_USERNAME,
    GITHUB_PASSWORD
)

GITHUB_URL_NEW_ISSUE = 'https://api.github.com/repos/{org}/{repo}/issues'
GITHUB_URL_NEW_MILESTONE = 'https://api.github.com/repos/{org}/{repo}/milestones'
GITHUB_URL_EDIT_ISSUE = 'https://api.github.com/repos/{org}/{repo}/issues/{issue}'
GITHUB_URL_NEW_COMMENT = 'https://api.github.com/repos/{org}/{repo}/issues/{issue}/comments'

JIRA_YEAR_START = 2008
JIRA_YEAR_END = 2018
JIRA_FILTER_TEMP = (
    'project={project} AND '
    'createdDate < {end}-01-01 AND '
    'createdDate >= {start}-01-01'
)

CLOSED_STATUSES = ('Resolved', 'Closed')
REQUEST_SLEEP = 15

def reformat_text(text):
    """
    Change the text formatting from Jira to GitHub flavoured Markdown.
    """

    replacements = (
        ('{noformat}', '```'),
        ('{quote}', '```'),
        ('{{', '`'),
        ('}}', '`')
    )

    for old, new in replacements:
        text = text.replace(old, new)

    return text

def decorate_user(user, text):
    """
    Adds a little preamble to a text body preserving who was its author.
    """

    return f"_{user.displayName} says:_ \n\n {text}"

def create_issue(repository_id, data, comments):
    """
    Create a issue in the GitHub repository.
    """

    org, repo = repository_id.split('/')

    session = requests.Session()
    session.auth = (GITHUB_USERNAME, GITHUB_PASSWORD)

    # Create the issue
    response = session.post(
        GITHUB_URL_NEW_ISSUE.format(org=org, repo=repo),
        json.dumps(data)
    )

    if response.status_code not in (200, 201):
        print(f'  Could not create: {data["title"]}')
        print(f'  Response: {response.content}')
        return

    time.sleep(REQUEST_SLEEP)

    # Get the ID of the newly created issue
    new_issue_id = json.loads(response.content)['number']

    # Set the status
    response = session.patch(
        GITHUB_URL_EDIT_ISSUE.format(org=org, repo=repo, issue=new_issue_id),
        json.dumps({'state': 'closed' if data['closed'] else 'open'})
    )

    if response.status_code not in (200, 201):
        print(f'  Could not edit status: {data["title"]}')
        print(f'  Response: {response.content}')
        #return

    print(f'  Successfully created: {data["title"]}')
    time.sleep(REQUEST_SLEEP)

    # Add the comments
    for i, comment in enumerate(comments):
        response = session.post(
            GITHUB_URL_NEW_COMMENT.format(org=org, repo=repo, issue=new_issue_id),
            json.dumps(comment)
        )
        if response.status_code == 201:
            print(f'    Successfully created comment {i}')
        else:
            print(f'    Could not create comment {i}')
            print(f'    Response: {response.content}')

        # Generate comments slowly
        time.sleep(REQUEST_SLEEP)

def generate_issue_data(issue, milestone_map):
    """
    Generates a issue data dict for given identifier.
    """

    data = {
        'title': f"[{issue.key}] {issue.fields.summary}",
        'body': decorate_user(issue.fields.creator, f"{reformat_text(issue.fields.description)}"),
        'closed': issue.fields.status.name in CLOSED_STATUSES,
        'labels': [issue.fields.issuetype.name.lower()],
        'milestone': milestone_map[issue.fields.fixVersions[0].name if issue.fields.fixVersions else 'Backlog']
    }

    if issue.fields.resolution:
        data['labels'].append(issue.fields.resolution.name.lower())

    comments = []
    for comment in issue.fields.comment.comments:
        comments.append({
            'body': decorate_user(comment.author, reformat_text(comment.body)),
        })

    return data, comments

def generate_milestone_map(repository_id, issues):
    """
    Creates all the milestones.
    """

    org, repo = repository_id.split('/')

    session = requests.Session()
    session.auth = (GITHUB_USERNAME, GITHUB_PASSWORD)

    milestone_map ={}
    milestones = list(sorted(set([
        issue.fields.fixVersions[0].name if issue.fields.fixVersions else 'Backlog'
        for issue in issues
    ])))

    for milestone in milestones:
        response = session.post(
            GITHUB_URL_NEW_MILESTONE.format(org=org, repo=repo),
            json.dumps({'title': milestone})
        )
        milestone_map[milestone] = json.loads(response.content)['number']
        time.sleep(REQUEST_SLEEP)

    return milestone_map

def download_attachments(issue):
    """
    Downloads the attachments from JIRA and saves them locally in the 'files/'
    folder.
    """

    if not issue.fields.attachment:
        return

    if not os.path.exists('files'):
        os.mkdir('files')

    for attachment in issue.fields.attachment:
        filename = f"files/{issue.key}_{attachment.filename}"
        with open(filename, 'wb') as f:
            f.write(attachment.get())

def generate_meta_comment(issue):
    """
    Store some metadata in a meta comment.
    """

    return {
            'body': f"```\nCreated: {issue.fields.created}\nModified: {issue.fields.updated}"
    }

def main(repo, project):
    jira = JIRA(JIRA_URL, basic_auth=[JIRA_USERNAME, JIRA_PASSWORD])

    print("Connection to JIRA successfully established.")
    print("Fetching list of matching issues...")

    # Get issue list for all the issues that match given project
    issue_list = []
    for year in range(JIRA_YEAR_START, JIRA_YEAR_END + 1):
        jira_filter = JIRA_FILTER_TEMP.format(project=project, start=year, end=year+1)
        issue_list += jira.search_issues(jira_filter, maxResults=5000)

    # Sort issue list
    sorted_issue_list = list(sorted(
        issue_list,
        key=lambda i: int(i.key.split('-')[1])
    ))

    print(f"Fetching milestones...")
    milestone_map = generate_milestone_map(repo, sorted_issue_list)

    print(f"The script will process {len(sorted_issue_list)} matching issues now.")

    issue = jira.issue(sorted_issue_list[0].key)
    for issue_key in [i.key for i in sorted_issue_list]:
        issue = jira.issue(issue_key)
        data, comments = generate_issue_data(issue, milestone_map)
        comments.insert(0, generate_meta_comment(issue))
        download_attachments(issue)
        create_issue(repo, data, comments)
        time.sleep(REQUEST_SLEEP)

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args['<repo>'], args['<project>'])
