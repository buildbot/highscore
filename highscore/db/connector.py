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
import json
from twisted.python import log
from twisted.application import service
from highscore.db import enginestrategy, pool, model

class DBConnector(service.MultiService):

    def __init__(self, highscore, config):
        service.MultiService.__init__(self)
        self.setName('highscore.db')
        self.highscore = highscore
        self.config = config

        db_url = config.db.get('url', 'sqlite:///highscore.sqlite')
        log.msg("Setting up database with URL %r" % (db_url,))

        # set up the engine and pool
        self._engine = enginestrategy.create_engine(db_url,
                              basedir=self.config.get('basedir'))
        self.model = model.Model(self)
        self.pool = pool.DBThreadPool(self._engine)

    def setup(self):
        d = self.model.is_current()
        @d.addCallback
        def check_current(res):
            if not res:
                log.msg("upgrading database")
                return self.model.upgrade()
        return d

    # state convenience methods
    #
    # Note that state handling is *not* parallelizable!

    def getState(self, name):
        def thd(conn):
            tbl = self.model.state
            res = conn.execute(
                sa.select([ tbl.c.value ], tbl.c.name == name))
            return res.fetchone()
        d = self.pool.do(thd)
        @d.addCallback
        def un_json(row):
            if row:
                return json.loads(row.value)
        return d

    def setState(self, name, value):
        value_json = json.dumps(value)
        def thd(conn):
            res = conn.execute(
                self.model.state.update(
                    self.model.state.c.name == name),
                    value=value_json)
            if res.rowcount:
                return
            conn.execute(
                self.model.state.insert(),
                name=name,
                value=value_json)
        return self.pool.do(thd)

