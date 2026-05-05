import os
import shutil
import tempfile
import time
import unittest
from unittest import mock
from git import Repo
from main import ChangeHandler, stage_commit_push

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
        handler = ChangeHandler(self.repo)
        event = mock.Mock()
        handler.on_any_event(event)
        self.assertTrue(handler.should_commit())
        self.assertFalse(handler.should_commit())

    @mock.patch('main.GITHUB_REMOTE', 'https://example.com/repo.git')
    @mock.patch('main.GITHUB_TOKEN', 'dummytoken')
    @mock.patch('main.COMMIT_AUTHOR', 'Tester <test@example.com>')
    def test_stage_commit_push(self):
        # make a file change
        with open(os.path.join(self.test_dir, 'foo.txt'), 'w') as f:
            f.write('change')
        self.repo.git.add('--all')
        self.assertTrue(self.repo.is_dirty())
        # Patch push method so we don't actually push
        with mock.patch.object(self.repo.git, 'push', return_value=None) as mock_push:
            stage_commit_push(self.repo)
            self.assertFalse(self.repo.is_dirty())
            mock_push.assert_called()
