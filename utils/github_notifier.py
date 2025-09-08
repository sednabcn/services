from github import Github
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def create_issue(repo_name, title, body):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_name)
    issue = repo.create_issue(title=title, body=body)
    return issue.number

def comment_issue(repo_name, issue_number, comment):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(number=issue_number)
    issue.create_comment(comment)
