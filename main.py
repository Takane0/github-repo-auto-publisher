import os
import sys
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from git import Repo, GitCommandError
from dotenv import load_dotenv

load_dotenv()

REPO_PATH = os.getenv('REPO_PATH')
GITHUB_REMOTE = os.getenv('GITHUB_REMOTE')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
COMMIT_AUTHOR = os.getenv('COMMIT_AUTHOR', 'AutoPublisher <auto@local>')

if not (REPO_PATH and GITHUB_REMOTE and GITHUB_TOKEN):
    print('Missing configuration. Check your .env file.')
    sys.exit(1)

def get_repo(path):
    try:
        repo = Repo(path)
        if 'origin' not in [r.name for r in repo.remotes]:
            repo.create_remote('origin', GITHUB_REMOTE)
        return repo
    except Exception as e:
        print(f'Error opening repo: {e}')
        sys.exit(1)

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, repo):
        self.repo = repo
        super().__init__()
        self._triggered = False
        self._lock = threading.Lock()

    def on_any_event(self, event):
        # Debounce, so multiple quick changes only make one commit
        with self._lock:
            self._triggered = True

    def should_commit(self):
        with self._lock:
            val = self._triggered
            self._triggered = False
            return val

def stage_commit_push(repo):
    try:
        repo.git.add('--all')
        # only commit if there are changes
        if repo.is_dirty(untracked_files=True):
            commit_msg = f'Auto commit at {time.strftime("%Y-%m-%d %H:%M:%S")}'
            repo.index.commit(commit_msg, author=COMMIT_AUTHOR)
            # build HTTPS url with token
            url_with_token = GITHUB_REMOTE.replace('https://', f'https://{GITHUB_TOKEN}@')
            repo.git.push(url_with_token, 'HEAD:main')
            print(f'Committed and pushed: {commit_msg}')
    except GitCommandError as e:
        print(f'Git error: {e}')


def main():
    if not os.path.isdir(REPO_PATH):
        print(f'Repo path does not exist: {REPO_PATH}')
        sys.exit(1)
    repo = get_repo(REPO_PATH)
    handler = ChangeHandler(repo)
    observer = Observer()
    observer.schedule(handler, REPO_PATH, recursive=True)
    observer.start()
    print(f'Watching {REPO_PATH} for file changes...')
    try:
        while True:
            time.sleep(2)
            if handler.should_commit():
                stage_commit_push(repo)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()
