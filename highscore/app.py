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
from highscore.managers import users, points

class Highscore(service.MultiService):

    def __init__(self, config):
        service.MultiService.__init__(self)
        self.setName("highscore")
        self.config = config
        self.is_set_up = False

    @defer.inlineCallbacks
    def setup(self):
        if self.is_set_up:
            return
        self.is_set_up = True

        self.db = dbconnector.DBConnector(self, self.config.get('db', {}))
        self.db.setServiceParent(self)
        yield self.db.setup()

        self.mq = mqconnector.MQConnector(self, self.config.get('mq', {}))
        self.mq.setServiceParent(self)
        self.mq.setup()

        self.users = users.UsersManager(self, self.config)
        self.users.setServiceParent(self)
        self.points = points.PointsManager(self, self.config)
        self.points.setServiceParent(self)

        for plugin_name in self.config.get('plugins', []):
            loader.load_plugin(plugin_name, self,
                    self.config['plugins'][plugin_name])

    def startService(self):
        # we want setup to complete *before* child services are initialized,
        # but startService is not ordinarily an async method.  So we just start
        # setting things up, and add child services once the setup is complete
        d = self.setup()
        @d.addCallback
        def chain(_):
            service.MultiService.startService(self)
