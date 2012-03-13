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
from twisted.python import log
from sqlalchemy.engine import strategies, url

class HighscoreEngineStrategy(strategies.ThreadLocalEngineStrategy):
    # A subclass of the ThreadLocalEngineStrategy that can effectively interact
    # with Highscore.
    # 
    # This adjusts the passed-in parameters to ensure that we get the behaviors
    # Highscore wants from particular drivers, and wraps the outgoing Engine
    # object so that its methods run in threads and return deferreds.

    name = 'highscore'

    def create(self, name_or_url, **kwargs):
        u = url.make_url(name_or_url)

        engine = strategies.ThreadLocalEngineStrategy.create(self,
                                            u, **kwargs)

        log.msg("setting database journal mode to 'wal'")
        try:
            engine.execute("pragma journal_mode = wal")
        except:
            log.msg("failed to set journal mode - database may fail")
        return engine

HighscoreEngineStrategy()

# this module is really imported for the side-effects, but pyflakes will like
# us to use something from the module -- so offer a copy of create_engine,
# which explicitly adds the strategy argument
def create_engine(*args, **kwargs):
    kwargs['strategy'] = 'highscore'
    return sa.create_engine(*args, **kwargs)
