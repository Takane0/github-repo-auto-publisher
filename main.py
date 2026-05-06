import os
import sys
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from git import Repo, GitCommandError
from dotenv import load_dotenv
from pathlib import Path
import fnmatch

load_dotenv()

REPO_PATH = os.getenv('REPO_PATH')
GITHUB_REMOTE = os.getenv('GITHUB_REMOTE')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
COMMIT_AUTHOR = os.getenv('COMMIT_AUTHOR', 'AutoPublisher <auto@local>')
COMMIT_PREFIX = os.getenv('COMMIT_PREFIX', '')

if not (REPO_PATH and GITHUB_REMOTE and GITHUB_TOKEN):
    print('Missing configuration. Check your .env file.')
    sys.exit(1)

# --- .gitignore handling ---
def parse_gitignore(gitignore_path):
    patterns = []
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, 'r') as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith('#'):
                    continue
                patterns.append(raw)
    return patterns

def match_gitignore(path, patterns, root):
    # path: absolute or relative path to file
    rel_path = os.path.relpath(path, root)
    for pat in patterns:
        if pat.endswith('/'):
            # directory ignore pattern
            if rel_path.startswith(pat.rstrip('/')):
                return True
        elif pat.startswith('/'):
            # match from project root
            if fnmatch.fnmatch(rel_path, pat.lstrip('/')):
                return True
        else:
            if fnmatch.fnmatch(rel_path, pat):
                return True
    return False


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
    def __init__(self, repo, ignored_patterns, root_path):
        self.repo = repo
        self._ignored_patterns = ignored_patterns
        self._root_path = root_path
        super().__init__()
        self._triggered = False
        self._lock = threading.Lock()

    def _is_ignored(self, src_path):
        # Ignore events in the git repo's .git/ folder
        rel_path = os.path.relpath(src_path, self._root_path)
        if rel_path.startswith('.git' + os.sep):
            return True
        return match_gitignore(src_path, self._ignored_patterns, self._root_path)

    def on_any_event(self, event):
        # Debounce, so multiple quick changes only make one commit
        if self._is_ignored(event.src_path):
            return
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
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            msg_prefix = COMMIT_PREFIX.strip()
            if msg_prefix:
                if not (msg_prefix.endswith(' ') or msg_prefix.endswith(':')):
                    msg_prefix += ' '
            commit_msg = f'{msg_prefix}Auto commit at {timestamp}'
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
    
    gitignore_file = os.path.join(REPO_PATH, '.gitignore')
    ignore_patterns = parse_gitignore(gitignore_file)
    repo = get_repo(REPO_PATH)
    handler = ChangeHandler(repo, ignore_patterns, REPO_PATH)
    observer = Observer()
    observer.schedule(handler, REPO_PATH, recursive=True)
    observer.start()
    print(f'Watching {REPO_PATH} for file changes...')
    if ignore_patterns:
        print('Respecting .gitignore patterns:')
        for pat in ignore_patterns:
            print(' ', pat)
    if COMMIT_PREFIX:
        print(f'Commit message prefix: "{COMMIT_PREFIX}"')
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
