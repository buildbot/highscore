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

import sqlalchemy as sa
from twisted.application import service

class UsersManager(service.MultiService):

    def __init__(self, highscore, config):
        service.MultiService.__init__(self)
        self.setName('highscore.users')
        self.highscore = highscore
        self.config = config
        self._typeCache = {}

    def _thd_getUserAttrTypeId(self, conn, type):
        # if it's cached, this is easy
        if type in self._typeCache:
            return self._typeCache[type]

        # otherwise, try to reload the cache
        tbl = self.highscore.db.model.user_attr_types
        for row in conn.execute(tbl.select()):
            self._typeCache[row.type] = row.id
        if type in self._typeCache:
            return self._typeCache[type]

        # otherwise, try to add it, handling collisions
        transaction = conn.begin()
        try:
            r = conn.execute(tbl.insert(), dict(type=type))
            id = r.inserted_primary_key[0]
            transaction.commit()
            self._typeCache[type] = id
            return id
        except (sa.exc.IntegrityError, sa.exc.ProgrammingError):
            transaction.rollback()
            # try again..
            return self._thd_getUserAttrTypeId(conn, type)

    def getUserIdAndName(self, matchInfo=[], suggestedInfo=[],
                         suggestedDisplayName=None):
        # info is represented as lists of tuples (type, value)

        def thd(conn, no_recurse=False):
            usersTbl = self.highscore.db.model.users
            infoTbl = self.highscore.db.model.users_info

            # try to find the user
            for type, value in matchInfo:
                matchTypeId = self._thd_getUserAttrTypeId(conn, type)
                res = conn.execute(sa.select(
                    [ usersTbl.c.display_name, usersTbl.c.id ],
                    (infoTbl.c.userid == usersTbl.c.id) &
                    (infoTbl.c.attrtypeid == matchTypeId) &
                    (infoTbl.c.value == value)))
                row = res.fetchone()
                res.close()
                if row:
                    return row.id, row.display_name

            # the user was not found, so we need to insert a new users entry
            # as well as the suggestedInfo.
            transaction = conn.begin()
            try:
                r = conn.execute(usersTbl.insert(),
                        dict(display_name=suggestedDisplayName))
                userid = r.inserted_primary_key[0]

                conn.execute(infoTbl.insert(), [
                    dict(userid=userid,
                         attrtypeid=self._thd_getUserAttrTypeId(conn, info[0]),
                         value=info[1])
                    for info in suggestedInfo ])
                transaction.commit()
            except (sa.exc.IntegrityError, sa.exc.ProgrammingError):
                transaction.rollback()

                # try it all over again, in case there was an overlapping,
                # identical call to findUserByAttr, but only retry once.
                if no_recurse:
                    raise
                return thd(conn, no_recurse=True)

            return userid, suggestedDisplayName
        return self.highscore.db.pool.do(thd)

    def getDisplayName(self, userid):
        def thd(conn):
            usersTbl = self.highscore.db.model.users
            r = conn.execute(sa.select([ usersTbl.c.display_name ],
                usersTbl.c.id == userid))
            row = r.fetchone()
            r.close()
            if row:
                return row.display_name
            else:
                return '(unknown)'
        return self.highscore.db.pool.do(thd)

