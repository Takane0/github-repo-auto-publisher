# GitHub Repo Auto-Publisher

A simple Python bot that watches a local folder for file changes and automatically pushes them to a specified GitHub repository. Great for automating backups or syncing folder changes to GitHub.

## Features
- Watches a folder for file changes (add, modify, delete).
- Stages, commits, and pushes updates to your GitHub repo.

## Requirements
- Python 3.7+
- Install dependencies:

    pip install -r requirements.txt

## Configuration

Create a `.env` file in the project root:

```
REPO_PATH=./my-local-repo-folder
GITHUB_REMOTE=https://github.com/yourusername/yourrepo.git
GITHUB_TOKEN=ghp_xxx123TOKENHERE456
COMMIT_AUTHOR=Your Name <your@email.com>
```
- `REPO_PATH`: Local path to the git repo folder to watch.
- `GITHUB_REMOTE`: GitHub repository URL (use the HTTPS format).
- `GITHUB_TOKEN`: GitHub personal access token (with `repo` scope).
- `COMMIT_AUTHOR`: Author string for commits.

## Usage

1. Make sure your folder (under `REPO_PATH`) is already initialized with `git init` and has the correct remote URL set (`origin`). The script will add the remote if necessary.
2. Start the watcher:

    python main.py

3. Make file changes inside the watched folder. The bot will detect, commit, and push them automatically.

## Run Tests

    python -m unittest discover tests

---

**Note:** Use this tool with **test repositories**! Unintended pushes to production repos can cause issues.
