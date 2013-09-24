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
import random
from highscore.plugins import base
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, defer
from twisted.python import log
from twisted.application import internet

# twisted.internet.ssl requires PyOpenSSL, so be resilient if it's missing
try:
    from twisted.internet import ssl
    have_ssl = True
except ImportError:
    have_ssl = False

class Plugin(base.Plugin):

    def __init__(self, highscore, config):
        base.Plugin.__init__(self, highscore, config)

        self.factory = IrcFactory(highscore, config)
        hostname = self.config.plugins.irc.get('hostname')
        assert hostname, 'no irc hostname supplied'
        port = self.config.plugins.irc.get('port', 6667)
        if self.config.plugins.irc.get('useSSL'):
            if not have_ssl:
                raise RuntimeError("useSSL requires PyOpenSSL")
            cf = ssl.ClientContextFactory()
            self.conn = internet.SSLClient(hostname, port, self.factory, cf)
        else:
            self.conn = internet.TCPClient(hostname, port, self.factory)

        self.conn.setServiceParent(self)


class IrcFactory(protocol.ClientFactory):

    def __init__(self, highscore, config):
        self.highscore = highscore
        self.config = config
        self.stay_connected = False

    def startService(self):
        self.stay_connected = True

    def stopService(self):
        self.stay_connected = False

    def buildProtocol(self, address):
        p = IrcProtocol(self.highscore, self.config)
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        if self.stay_connected:
            lostDelay = random.randint(1, 5)
            reactor.callLater(lostDelay, connector.connect)

    def clientConnectionFailed(self, connector, reason):
        if self.stay_connected:
            failedDelay = random.randint(45, 60)
            reactor.callLater(failedDelay, connector.connect)


class IrcProtocol(irc.IRCClient):

    def __init__(self, highscore, config):
        self.highscore = highscore
        self.config = config
        self.channel = self.config.plugins.irc.channel
        self.nickname = self.config.plugins.irc.nickname
        self.in_channel = False
        self.mq_consumers = []

    def begin(self):
        # we're initialized; begin interacting
        if self.in_channel:
            return
        log.msg("IRC bot joined to '%s'" % (self.channel,))
        self.highscore.mq.produce('irc.connected', {})
        self.in_channel = True
        cons = self.mq_consumers = []
        cons.append(self.highscore.mq.consume(
                self.mqOutgoingMessage, 'irc.outgoing'))
        for ann in self.config.plugins.irc.get('announce', []):
            cons.append(self.highscore.mq.consume(
                    self.mqAnnounce, 'announce.%s' % (ann,)))

    def end(self):
        # we're not connected anymore; end interactions
        self.in_channel = False
        self.highscore.mq.produce('irc.disconnected', {})
        for cons in self.mq_consumers:
            cons.stop_consuming()
        self.mq_consumers = []

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        log.msg("IRC bot connected to '%s'"
                    % (self.config.plugins.irc.hostname,))

    def connectionLost(self, reason):
        log.msg("IRC bot disconnected from '%s'"
                    % (self.config.plugins.irc.hostname,))
        irc.IRCClient.connectionLost(self, reason)
        self.end()

    def signedOn(self):
        self.join(self.channel)

    def joined(self, channel):
        if channel == self.channel:
            self.begin()

    plusplus_re = re.compile(r'^([^ ]*)\+\+(.*)')
    def privmsg(self, user, channel, msg):
        nick = user.split('!', 1)[0]
        if channel == self.nickname:
            # private message
            self.msg(nick, "let's keep it in channel, k?")
            return

        if msg.startswith('top_ten'):
           self.sendTopTen(nick)
           return

        if msg.startswith(self.nickname + ":"):
            d = self.handleMessage(nick, msg[len(self.nickname)+1:].strip())
            d.addErrback(log.msg, "while handling incoming IRC message")
            return

        # handle e.g., dustin++ for being so awesome
        mo = self.plusplus_re.match(msg)
        if mo:
            d = self.addPoints(mo.group(1), 1, nick, mo.group(2))
            d.addErrback(log.msg, "while adding points in response to IRC")
            return

    def msg(self, channel, message):
        # wrap message into utf-8 if necessary
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        irc.IRCClient.msg(self, channel, message)

    def publicMsg(self, msg):
        if isinstance(msg, unicode):
           msg = msg.encode('utf-8')
        self.highscore.mq.produce('announce.points',
                                  dict(message=msg))

    @defer.inlineCallbacks
    def handleMessage(self, nick, msg):
        userid, name = yield self.getUserIdAndName(nick)
        self.highscore.mq.produce(
                'irc.incoming',
                dict(message=msg, nick=nick, display_name=name, userid=userid))

    @defer.inlineCallbacks
    def getUserIdAndName(self, nick):
        userid, name = yield self.highscore.users.getUserIdAndName(
                matchInfo=[('irc_nick', nick)],
                suggestedInfo=[('irc_nick', nick)],
                suggestedDisplayName=nick)
        defer.returnValue((userid, name))

    @defer.inlineCallbacks
    def addPoints(self, dest_nick, points, source_nick, comments):
        comments = comments.strip()
        if not comments:
            comments = "from %s in irc" % (source_nick,)
        if source_nick == dest_nick and points > 0:
            points = -5
            comments = "for being greedy"
        userid, _ = \
                yield self.getUserIdAndName(dest_nick)
        yield self.highscore.points.addPoints(userid=userid, points=points,
                                              comments=comments)

    def posSuffixStr(self, pos):
        if pos == 1:
           posstr = 'st'
        elif pos == 2:
           posstr = 'nd'
        elif pos == 3:
           posstr = 'rd'
        else:
           posstr = 'th'

        if pos < 10:
           pref = ' '
        else:
           pref = ''
 
        return pref + str(pos) + posstr
    

    def sendTopTen(self, nick):
        hs = self.highscore.points.getHighscores()
        @hs.addCallback
        def printData(data):
            i = 1 
            self.publicMsg("Top Ten Buildbot Contributors")
            for item in data:
                self.publicMsg(self.posSuffixStr(i) + " " +
                               item['display_name'] + " " +
                               str(item['points']))
                i += 1
            if i < 10:
               for j in range(11): 
                   if j >= i:
                      self.publicMsg(self.posSuffixStr(j) + " ** empty **")

    # handle messages from other systems
    def mqOutgoingMessage(self, routing_key, data):
        self.msg(self.channel, data['message'])

    def mqAnnounce(self, routing_key, data):
        self.msg(self.channel, data['message'])
