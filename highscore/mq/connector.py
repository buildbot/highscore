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
from twisted.python.reflect import namedObject

class MQConnector(service.MultiService):

    classes = {
        'simple' : "highscore.mq.simple.SimpleMQ",
    }

    def __init__(self, highscore, config):
        service.MultiService.__init__(self)
        self.setName('highscore.mq')
        self.highscore = highscore
        self.config = config
        self.impl = None # set in setup
        self.impl_type = None # set in setup

    def setup(self):
        assert not self.impl

        # imports are done locally so that we don't try to import
        # implementation-specific modules unless they're required.
        typ = self.config.mq.get('type', 'simple')
        assert typ in self.classes # this is checked by MasterConfig
        self.impl_type = typ
        cls = namedObject(self.classes[typ])
        self.impl = cls(self.highscore, self.config)

        # set up the impl as a child service
        self.impl.setServiceParent(self)

        # copy the methods onto this object for ease of access
        self.produce = self.impl.produce
        self.consume = self.impl.consume

    def produce(self, routing_key, data):
        # will be patched after configuration to point to the running
        # implementation's method
        raise NotImplementedError

    def consume(self, callback, *topics, **kwargs):
        # will be patched after configuration to point to the running
        # implementation's method
        raise NotImplementedError
