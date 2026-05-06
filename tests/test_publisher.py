import os
import shutil
import tempfile
import time
import unittest
from unittest import mock
from git import Repo
from main import ChangeHandler, stage_commit_push, parse_gitignore, match_gitignore

class TestPublisher(unittest.TestCase):
    def setUp(self):
        # Setup a temp git repo
        self.test_dir = tempfile.mkdtemp()
        self.repo = Repo.init(self.test_dir)
        (open(os.path.join(self.test_dir, 'test.txt'), 'w')).close()
        self.repo.git.add('--all')
        self.repo.index.commit('init')
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_change_handler_trigger(self):
        handler = ChangeHandler(self.repo, [], self.test_dir)
        event = mock.Mock()
        event.src_path = os.path.join(self.test_dir, 'afile.txt')
        handler.on_any_event(event)
        self.assertTrue(handler.should_commit())
        self.assertFalse(handler.should_commit())

    def test_gitignore_parser_and_match(self):
        # Simulate .gitignore content
        patterns = ['node_modules/', '*.tmp', 'secret.txt']
        root = self.test_dir
        node_mod_dir = os.path.join(root, 'node_modules', 'pkg')
        foo_tmp = os.path.join(root, 'foo.tmp')
        secret = os.path.join(root, 'secret.txt')
        not_ignored = os.path.join(root, 'keepme.py')
        os.makedirs(node_mod_dir)
        self.assertTrue(match_gitignore(node_mod_dir, patterns, root))
        self.assertTrue(match_gitignore(foo_tmp, patterns, root))
        self.assertTrue(match_gitignore(secret, patterns, root))
        self.assertFalse(match_gitignore(not_ignored, patterns, root))

    @mock.patch('main.GITHUB_REMOTE', 'https://example.com/repo.git')
    @mock.patch('main.GITHUB_TOKEN', 'dummytoken')
    @mock.patch('main.COMMIT_AUTHOR', 'Tester <test@example.com>')
    def test_stage_commit_push(self):
        # make a file change
        with open(os.path.join(self.test_dir, 'foo.txt'), 'w') as f:
            f.write('change')
        self.repo.git.add('--all')
        self.assertTrue(self.repo.is_dirty())
        with mock.patch.object(self.repo.git, 'push', return_value=None) as mock_push, \
             mock.patch('main.COMMIT_PREFIX', '[BOT] '):
            stage_commit_push(self.repo)
            self.assertFalse(self.repo.is_dirty())
            mock_push.assert_called()
            # Check commit message includes prefix
            latest = self.repo.head.commit.message
            self.assertTrue(latest.startswith('[BOT] '))
