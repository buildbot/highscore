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

from distutils.core import setup

setup(
    name='highscore',
    version='1.0',
    description='High-score tracking for projects',
    author='Dustin J. Mitchell',
    author_email='dustin@cs.uchicago.edu',
    packages=['highscore'],
    install_requires=[
        'twisted >= 11.0.0',
        'sqlalchemy >= 0.6.0, <= 0.7.10',
        'sqlalchemy-migrate == 0.7.2',
        'pyopenssl',
        'txgithub',
    ],
)
