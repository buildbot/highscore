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

import random
import hashlib
import json
from twisted.python import log, failure
from twisted.application import service
from twisted.internet import reactor, defer
from highscore.www import resource

class GithubHookListener(service.Service):
    # a listener for repo hooks that incorporates a randomized hookToken to
    # prevent spoofing

    known_events = [ 'push', 'issues', 'issue_comment', 'commit_comment',
            'pull_request' ]

    def __init__(self, plugin, highscore, config):
        self.setName('plugins.github.listener')
        self.plugin = plugin
        self.highscore = highscore
        self.config = config
        self.listeningEvents = config.plugins.github.get('events',
                                                    self.known_events)

        # set in startService
        self.hookToken = None
        self.startupDeferred = None

        # this goes in the plugin's 'www' attribute
        self.www = RootResource(self, highscore)

    def startService(self):
        self.startupDeferred = d = self.configHooks()
        @d.addCallback
        def done(_):
            self.startupDeferred = None
        d.addErrback(log.err, 'while configuring github hooks',
                                system='github')

    def stopService(self):
        return self.startupDeferred

    @defer.inlineCallbacks
    def _getHookKey(self):
        if self.hookToken:
            return

        self.hookToken = yield self.highscore.db.getState('github.hookToken')
        if self.hookToken:
            return

        hash = hashlib.md5()
        hash.update(str(random.random()))
        hash.update(str(self.config))
        self.hookToken = hash.hexdigest()[:16]

        yield self.highscore.db.setState('github.hookToken', self.hookToken)

    @defer.inlineCallbacks
    def configHooks(self):
        # synchronize github's list of hooks with what we need, claiming
        # anything with our URL as a prefix as our own.

        # make sure we have the hook key
        yield self._getHookKey()

        base_url = self.highscore.www.makeUrl('plugins', 'github')

        api = self.plugin.api
        github_cfg = self.config.plugins.github
        for monitored_repo in github_cfg.get('monitor_repos', []):
            repo_user, repo_name = monitored_repo
            all_hooks = yield api.repos.getHooks(repo_user, repo_name)

            # filter out hooks we don't want to touch
            my_hooks = [ h for h in all_hooks
                    if h['name'] == 'web' and h['active'] and
                       h['config']['url'].startswith(base_url) ]

            current_hook_urls = set([ h['config']['url'] for h in my_hooks ])
            exp_hook_urls = set([ '%s/%s/%s' % (base_url, self.hookToken, evt)
                              for evt in self.listeningEvents ])
            for url in exp_hook_urls - current_hook_urls:
                log.msg('adding hook %s' % (url,), system='github')
                evt = url.split('/')[-1]
                yield api.repos.createHook(repo_user, repo_name,
                        name='web', config=dict(url=url), events=[ evt ],
                        active=True)
            for url in current_hook_urls - exp_hook_urls:
                log.msg('removing hook %s' % (url,), system='github')
                # find the id
                id = [ h['id'] for h in my_hooks
                       if h['config']['url'] == url ][0]
                yield api.repos.deleteHook(repo_user, repo_name, id)

    def handleEvent(self, evt_type, payload):
        d = self._handleEvent(evt_type, payload)
        d.addErrback(log.err, 'while handling a %s event' % (evt_type,),
                system='github')

    @defer.inlineCallbacks
    def _handleEvent(self, evt_type, payload):
        userid = None
        if evt_type == 'push':
            githubUsername = payload['pusher']['name']
        else:
            githubUsername = payload['sender']['login']
        userid, displayName = yield self.highscore.users.getUserIdAndName(
                matchInfo=[ ('github-username', githubUsername) ],
                suggestedInfo=[ ('github-username', githubUsername) ],
                suggestedDisplayName=githubUsername)

        self.highscore.mq.produce('github.event.%s' % (evt_type,),
            dict(event_type=evt_type,
                    userid=userid,
                    display_name=displayName,
                    payload=payload))


class RootResource(resource.Resource):
    # /plugins/github

    def __init__(self, listener, highscore):
        resource.Resource.__init__(self, highscore)
        self.listener = listener
        self.hook = HookResource(listener, highscore)

    def getChild(self, name, request):
        if name != self.listener.hookToken:
            return resource.Resource.getChild(self, name, request)
        return self.hook


class HookResource(resource.Resource):
    # /plugins/github/$hookToken

    def __init__(self, listener, highscore):
        resource.Resource.__init__(self, highscore)
        self.endpoints = {}
        for evt_type in listener.listeningEvents:
            rsrc = EventResource(evt_type, listener, highscore)
            self.putChild(evt_type, rsrc)


class EventResource(resource.Resource):
    # /plugins/github/$hookToken/$evt_type

    def __init__(self, evt_type, listener, highscore):
        resource.Resource.__init__(self, highscore)
        self.listener = listener
        self.evt_type = evt_type

    def render(self, request):
        try:
            payload = json.loads(request.args['payload'][0])
            reactor.callLater(0, lambda :
                self.listener.handleEvent(self.evt_type, payload))
        except Exception:
            log.err(failure.Failure(), "in Github web hook", system='github')
        return '{}\n'
