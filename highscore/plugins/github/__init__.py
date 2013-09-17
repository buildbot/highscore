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

import re
from twisted.python import log
from highscore.plugins import base
from highscore.plugins.github import listener
from txgithub import api

class Plugin(base.Plugin):

    def __init__(self, highscore, config):
        base.Plugin.__init__(self, highscore, config)
        self.setName('plugins.github')

        self.mq_consumers = []

        # turn on the listener and set it as our www attribute so it can get
        # called from github - it will register itself
        self.listener = listener.GithubHookListener(self, highscore, config)
        self.listener.setServiceParent(self)
        self.www = self.listener.www

        # set up the Github API for general use
        oauth2_token = config.plugins.github.oauth2_token
        if not oauth2_token:
            log.msg('No oauth2_token specified; run get-github-token.py',
                    system='github')
        self.api = api.GithubApi(oauth2_token)

    def startService(self):
        base.Plugin.startService(self)
        cons = self.mq_consumers = []
        prefix = 'mqHandle_'
        for attrname in dir(self):
            if not attrname.startswith(prefix):
                continue
            hook_type = attrname[len(prefix):]
            method = getattr(self, attrname)
            cons.append(self.highscore.mq.consume(
                method, "github.event.%s" % (hook_type,)))

    def stopService(self):
        consumers = self.mq_consumers
        while consumers:
            cons = consumers.pop()
            cons.stop_consuming()
        return base.Plugin.stopService(self)

    # handle messages by announcing them and awarding points

    ws_re = re.compile(r'\s+')
    def _truncateText(self, text):
        text = self.ws_re.sub(' ', text)
        if len(text) > 100:
            text = text[:100] + '...'
        return text

    def _truncateSha1(self, text):
        return text[:8]

    def mqHandle_push(self, key, message):
        truncText = self._truncateText
        truncSha1 = self._truncateSha1

        # announce
        subs = {}
        subs['commitMsg'] = truncText(
                message['payload']['head_commit']['message'])
        subs['commitSha1'] = truncSha1(message['payload']['head_commit']['id'])
        subs['repoOwner'] = message['payload']['repository']['owner']['name']
        subs['repoName'] = message['payload']['repository']['name']
        subs['displayName'] = message['display_name']

        annText = ("%(displayName)s pushed to "
                   "%(repoOwner)s/%(repoName)s: %(commitMsg)s" % subs)
        self.highscore.mq.produce('announce.github.push',
                                  dict(message=annText))

        # award points
        self.highscore.points.addPoints(
                userid=message['userid'],
                points=1,
                comments='for pushing %(commitSha1)s to '
                         '%(repoOwner)s/%(repoName)s' % subs)

    def mqHandle_issue_comment(self, key, message):
        truncText = self._truncateText

        # announce
        subs = {}
        issue = message['payload']['issue']
        if issue.get('pull_request'):
            subs['issueOrPull'] = 'pull request'
        else:
            subs['issueOrPull'] = 'issue'
        subs['number'] = issue['number']
        subs['comment'] = truncText(message['payload']['comment']['body'])
        subs['displayName'] = message['display_name']

        annText = ("%(displayName)s commented on (%(issueOrPull)s) "
                   "#%(number)s: %(comment)s" % subs)
        self.highscore.mq.produce('announce.github.issue_comment',
                                  dict(message=annText))

        # award points
        self.highscore.points.addPoints(
                userid=message['userid'],
                points=1,
                comments='for %(issueOrPull)s #%(number)s comment: '
                         '%(comment)s' % subs)

    actionGerunds = dict(
            opened='opening', closed='closing', reopened='reopening')
    def mqHandle_issues(self, key, message):
        truncText = self._truncateText

        # announce
        subs = {}
        issue = message['payload']['issue']
        if issue.get('pull_request'):
            subs['issueOrPull'] = 'pull request'
        else:
            subs['issueOrPull'] = 'issue'
        subs['number'] = issue['number']
        subs['title'] = truncText(message['payload']['issue']['title'])
        subs['action'] = message['payload']['action']
        subs['actioning'] = self.actionGerunds[subs['action']]
        subs['displayName'] = message['display_name']

        annText = ("%(displayName)s %(action)s (%(issueOrPull)s) "
                   "#%(number)s: %(title)s" % subs)
        self.highscore.mq.produce('announce.github.issues',
                                  dict(message=annText))

        # award points
        self.highscore.points.addPoints(
                userid=message['userid'],
                points=1,
                comments='for %(actioning)s %(issueOrPull)s #%(number)s: '
                         '%(title)s' % subs)

    def mqHandle_commit_comment(self, key, message):
        truncText = self._truncateText

        # announce
        subs = {}
        subs['comment'] = truncText(message['payload']['comment']['body'])
        subs['commentUrl'] = message['payload']['comment']['html_url']
        subs['displayName'] = message['display_name']

        annText = ("%(displayName)s commented (%(commentUrl)s): %(comment)s"
                    % subs)
        self.highscore.mq.produce('announce.github.commit_comment',
                                  dict(message=annText))

        # award points
        self.highscore.points.addPoints(
                userid=message['userid'],
                points=1,
                comments='for commit comment %(commentUrl)s' % subs)

    def mqHandle_pull_request(self, key, message):
        truncText = self._truncateText

        # announce
        subs = {}
        subs['number'] = message['payload']['number']
        subs['title'] = truncText(message['payload']['pull_request']['title'])
        subs['action'] = message['payload']['action']
        subs['actioning'] = self.actionGerunds[subs['action']]
        subs['displayName'] = message['display_name']

        annText = ("%(displayName)s %(action)s (%(issueOrPull)s) "
                   "#%(number)s: %(title)s" % subs)
        self.highscore.mq.produce('announce.github.pull_request',
                                  dict(message=annText))

        # award points
        self.highscore.points.addPoints(
                userid=message['userid'],
                points=1,
                comments='for %(actioning)s %(issueOrPull)s #%(number)s: '
                         '%(title)s' % subs)

