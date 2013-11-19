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
import migrate
import migrate.versioning.schema
import migrate.versioning.repository
from twisted.python import util, log

try:
    from migrate.versioning import exceptions
    _hush_pyflakes = exceptions
except ImportError:
    from migrate import exceptions

class Model(object):

    def __init__(self, db):
        self.db = db

    metadata = sa.MetaData()

    #
    # schema
    #

    users = sa.Table('users', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('display_name', sa.Text, nullable=False),
    )

    user_attr_types = sa.Table('user_attr_types', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('type', sa.String(256), unique=True, nullable=False),
    )

    users_info = sa.Table('users_info', metadata,
        sa.Column('userid', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('attrtypeid', sa.Integer,
                    sa.ForeignKey('user_attr_types.id')),
        sa.Column('value', sa.String(256), nullable=False),
    )
    sa.Index('users_info_attr_value',
            users_info.c.attrtypeid,
            users_info.c.value,
            unique=True)

    points = sa.Table('points', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('userid', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('when', sa.Integer, nullable=False), # epoch time
        sa.Column('points', sa.Integer, nullable=False),
        sa.Column('comments', sa.Text, nullable=False),
    )
    sa.Index('points_userid', points.c.userid)

    # storage for arbitrary small state
    state = sa.Table('state', metadata,
        sa.Column('name', sa.Text, primary_key=True),
        sa.Column('value', sa.Text, nullable=False),
    )

    #
    # migration support
    #

    repo_path = util.sibpath(__file__, "migrate")

    def is_current(self):
        def thd(engine):
            repo = migrate.versioning.repository.Repository(self.repo_path)
            repo_version = repo.latest
            try:
                # migrate.api doesn't let us hand in an engine
                schema = migrate.versioning.schema.ControlledSchema(engine,
                                                                self.repo_path)
                db_version = schema.version
            except exceptions.DatabaseNotControlledError:
                return False

            return db_version == repo_version
        return self.db.pool.do_with_engine(thd)

    def upgrade(self):
        # http://code.google.com/p/sqlalchemy-migrate/issues/detail?id=100
        # means  we cannot use the migrate.versioning.api module.  So these
        # methods perform similar wrapping functions to what is done by the API
        # functions, but without disposing of the engine.
        def thd(engine):
            try:
                schema = migrate.versioning.schema.ControlledSchema(engine,
                    self.repo_path)
            except exceptions.DatabaseNotControlledError:
                migrate.versioning.schema.ControlledSchema.create(engine,
                        self.repo_path, None)
                schema = migrate.versioning.schema.ControlledSchema(engine,
                    self.repo_path)
            changeset = schema.changeset(None)
            for version, change in changeset:
                log.msg('migrating schema version %s -> %d'
                        % (version, version + 1))
                schema.runchange(version, change, 1)
        return self.db.pool.do_with_engine(thd)

# migrate has a bug in one of its warnings; this is fixed in version control
# (3ba66abc4d), but not yet released. It can't hurt to fix it here, too, so we
# get realistic tracebacks
try:
    import migrate.versioning.exceptions as ex1
    import migrate.changeset.exceptions as ex2
    ex1.MigrateDeprecationWarning = ex2.MigrateDeprecationWarning
except (ImportError,AttributeError):
    pass
