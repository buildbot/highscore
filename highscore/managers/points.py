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
from datetime import datetime
from twisted.application import service

class PointsManager(service.MultiService):

    def __init__(self, highscore, config):
        service.MultiService.__init__(self)
        self.setName('highscore.points')
        self.highscore = highscore
        self.config = config

    @defer.inlineCallbacks
    def addPoints(self, userid, points, comments):
        def thd(conn):
            tbl = self.highscore.db.model.points
            r = conn.execute(tbl.insert(), dict(
                userid=userid,
                when=datetime.utcnow(),
                points=points,
                comments=comments))
            pointsid = r.inserted_primary_key[0]
            return pointsid
        pointsid = yield self.highscore.db.pool.do(thd)

        display_name = yield self.highscore.users.getDisplayName(userid)
        self.highscore.mq.produce('points.add.%d' % userid,
                dict(pointsid=pointsid, userid=userid,
                        display_name=display_name, points=points,
                        comments=comments))
