# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

from twisted.internet import defer
from twisted.application import service
from highscore.plugins import loader
from highscore.db import connector as dbconnector
from highscore.mq import connector as mqconnector
from highscore.www import service as wwwservice
from highscore.managers import users, points

class Highscore(service.MultiService):

    def __init__(self, config):
        service.MultiService.__init__(self)
        self.setName("highscore")
        self.config = Config(config)
        self.basedir = config.get('basedir')
        self.is_set_up = False

    @defer.inlineCallbacks
    def setup(self):
        if self.is_set_up:
            return
        self.is_set_up = True
        print self.config
        self.db = dbconnector.DBConnector(self, self.config)
        self.db.setServiceParent(self)
        yield self.db.setup()

        self.mq = mqconnector.MQConnector(self, self.config)
        self.mq.setServiceParent(self)
        self.mq.setup()

        self.users = users.UsersManager(self, self.config)
        self.users.setServiceParent(self)

        self.points = points.PointsManager(self, self.config)
        self.points.setServiceParent(self)

        self.www = wwwservice.WWWService(self, self.config)
        self.www.setServiceParent(self)

        self.plugins = {}
        for plugin_name in self.config.plugins:
            self.plugins[plugin_name] = loader.load_plugin(
                plugin_name, self, self.config)

    def startService(self):
        # we want setup to complete *before* child services are initialized,
        # but startService is not ordinarily an async method.  So we just start
        # setting things up, and add child services once the setup is complete
        d = self.setup()
        @d.addCallback
        def chain(_):
            service.MultiService.startService(self)


class Config(object):
    """Allow attribute access to configuration, with default values"""

    class _NoArg:
        pass

    def __init__(self, dict):
        self._dict = dict

    def __iter__(self):
        return self._dict.__iter__()

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()

    def __repr__(self):
        return self._dict.__repr__()

    def __getitem__(self, k):
        return self._get(k, wantKeyError=True)

    def get(self, k, default=None):
        return self._get(k, default)

    def __nonzero__(self):
        return bool(self._dict)

    def __getattr__(self, k):
        if k[0] == '_':
            return object.__getattr__(k)
        return self._get(k)

    def _get(self, k, default=_NoArg, wantKeyError=False):
        if k in self._dict:
            v = self._dict[k]
            if isinstance(v, dict):
                return Config(v)
            else:
                return v
        else:
            if default is not self._NoArg:
                return default
            elif wantKeyError:
                return self._dict[k]
            return Config({})
