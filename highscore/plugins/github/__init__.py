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

        self.mq_consumers = []

        # turn on the listener and set it as our www attribute so it can get
        # called from github - it will register itself
        self.listener = listener.GithubHookListener(self, highscore, config)
        self.listener.setServiceParent(self)
        self.www = self.listener.www

        # set up the Github API for general use
        self.api = api.GithubApi(config.get('username'),
                                 config.get('password'))

    def startService(self):
        base.Plugin.startService(self)
        cons = self.mq_consumers = []
        cons.append(self.highscore.mq.consume(
                self.mqCommitComment, 'github.event.commit_comment'))

    def stopService(self):
        for cons in self.mq_consumers:
            cons.stop_consuming()
        self.mq_consumers = []
        return base.Plugin.stopService(self)

    def mqCommitComment(self, key, message):
        self.highscore.points.addPoints(
                userid=message['userid'],
                points=1,
                comments='for a commit comment')
