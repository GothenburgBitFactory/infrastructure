from jira import JIRA

from config import (
    JIRA_USERNAME,
    JIRA_PASSWORD,
    JIRA_URL,
    GITHUB_USERNAME,
    GITHUB_PASSWORD
)

jira = JIRA(JIRA_URL, basic_auth=[JIRA_USERNAME, JIRA_PASSWORD])
