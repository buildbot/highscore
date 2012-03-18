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

from highscore.plugins import base
from highscore.plugins.github import listener
from highscore.plugins.github import api

class Plugin(base.Plugin):

    def __init__(self, highscore, config):
        base.Plugin.__init__(self, highscore, config)

        # turn on the listener and set it as our www attribute
        self.listener = listener.GithubHookListener(self, highscore, config)
        self.listener.setServiceParent(self)
        self.www = self.listener.www

        self.api = api.GithubApi(config.get('username'),
                                 config.get('password'))
