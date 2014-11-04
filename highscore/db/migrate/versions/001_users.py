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

def upgrade(migrate_engine):
    metadata = sa.MetaData()
    metadata.bind = migrate_engine

    users = sa.Table('users', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('display_name', sa.Text, nullable=False),
    )
    users.create()

    user_attr_types = sa.Table('user_attr_types', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('type', sa.String(256), unique=True, nullable=False),
    )
    user_attr_types.create()

    users_info = sa.Table('users_info', metadata,
        sa.Column('userid', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('attrtypeid', sa.Integer,
                    sa.ForeignKey('user_attr_types.id')),
        sa.Column('value', sa.String(256), nullable=False),
    )
    users_info.create()

    sa.Index('users_info_attr_value',
            users_info.c.attrtypeid,
            users_info.c.value,
            unique=True).create()
