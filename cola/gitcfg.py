import os
import sys
import copy

from cola import core
from cola import gitcmd


_config = None
def instance():
    """Return a static GitConfig instance."""
    global _config
    if not _config:
        _config = GitConfig()
    return _config


def _appendifexists(category, path, result):
    try:
        mtime = os.stat(path).st_mtime
        result.append((category, path, mtime))
    except OSError:
        pass


def _stat_info():
    data = []
    # Try /etc/gitconfig as a fallback for the system config
    _appendifexists('system', '/etc/gitconfig', data)
    _appendifexists('user', os.path.expanduser('~/.gitconfig'), data)
    _appendifexists('repo', gitcmd.instance().git_path('config'), data)
    return data


class GitConfig(object):
    """Encapsulate access to git-config values."""

    def __init__(self):
        self.git = gitcmd.instance()
        self._system = {}
        self._user = {}
        self._repo = {}
        self._cache_key = None
        self._configs = []
        self._config_files = {}
        self._find_config_files()

    def reset(self):
        self._system = {}
        self._user = {}
        self._repo = {}
        self._configs = []
        self._config_files = {}
        self._find_config_files()

    def user(self):
        return copy.deepcopy(self._user)

    def repo(self):
        return copy.deepcopy(self._repo)

    def _find_config_files(self):
        """
        Classify git config files into 'system', 'user', and 'repo'.

        Populates self._configs with a list of the files in
        reverse-precedence order.  self._config_files is populated with
        {category: path} where category is one of 'system', 'user', or 'repo'.

        """
        # Try the git config in git's installation prefix
        statinfo = _stat_info()
        self._configs = map(lambda x: x[1], statinfo)
        self._config_files = {}
        for (cat, path, mtime) in statinfo:
            self._config_files[cat] = path

    def update(self):
        """Read config values from git."""
        if self._cached():
            return
        self._read_configs()

    def _cached(self):
        """
        Return True when the cache matches.

        Updates the cache and returns False when the cache does not match.

        """
        cache_key = _stat_info()
        if not self._cache_key or cache_key != self._cache_key:
            self._cache_key = cache_key
            return False
        return True

    def _read_configs(self):
        """Read git config value into the system, user and repo dicts."""
        self.reset()

        if 'system' in self._config_files:
            self._system = self.read_config(self._config_files['system'])

        if 'user' in self._config_files:
            self._user = self.read_config(self._config_files['user'])

        if 'repo' in self._config_files:
            self._repo = self.read_config(self._config_files['repo'])

    def read_config(self, path):
        """Return git config data from a path as a dictionary."""
        dest = {}
        args = ('--null', '--file', path, '--list')
        config_lines = self.git.config(*args).split('\0')
        for line in config_lines:
            try:
                k, v = line.split('\n')
            except:
                # the user has an invalid entry in their git config
                continue
            v = core.decode(v)
            if v == 'true' or v == 'false':
                v = bool(eval(v.title()))
            try:
                v = int(eval(v))
            except:
                pass
            dest[k] = v
        return dest

    def get(self, key, default=None):
        """Return the string value for a config key."""
        self.update()
        for dct in (self._repo, self._user, self._system):
            if key in dct:
                return dct[key]
        return default

    def get_encoding(self, default='utf-8'):
        return self.get('gui.encoding', default=default)