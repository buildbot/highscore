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

from twisted.application import service
from highscore.plugins import loader
from highscore.db import connector as dbconnector
from highscore.mq import connector as mqconnector

class Highscore(service.MultiService):

    def __init__(self, config):
        service.MultiService.__init__(self)
        self.setName("highscore")
        self.config = config

        self.db = dbconnector.DBConnector(self, config.get('db', {}))
        self.mq = mqconnector.MQConnector(self, config.get('mq', {}))

        for plugin_name in config.get('plugins', []):
            loader.load_plugin(plugin_name, self,
                    config['plugins'][plugin_name])
