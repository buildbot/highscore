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
from highscore.plugins import base
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
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
        hostname = self.config.get('hostname')
        assert hostname, 'no irc hostname supplied'
        port = self.config.get('port', 6667)
        if self.config.get('useSSL'):
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
        self.channel = self.config['channel']
        self.nickname = self.config['nickname']
        self.in_channel = False

    def begin(self):
        # we're initialized; begin interacting
        if self.in_channel:
            return
        log.msg("IRC bot joined to '%s'" % (self.channel,))
        self.highscore.mq.produce('irc.connected', {})
        self.in_channel = True
        self.mq_consumer = self.highscore.mq.consume(
                self.mqMessage, 'irc.outgoing')

    def end(self):
        # we're not connected anymore; end interactions
        self.in_channel = False
        self.highscore.mq.produce('irc.disconnected', {})
        if self.mq_consumer:
            self.mq_consumer.stop_consuming()

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        log.msg("IRC bot connected to '%s'" % (self.config['hostname']))

    def connectionLost(self, reason):
        log.msg("IRC bot disconnected from '%s'" % (self.config['hostname']))
        irc.IRCClient.connectionLost(self, reason)
        self.end()

    def signedOn(self):
        self.join(self.channel)

    def joined(self, channel):
        if channel == self.channel:
            self.begin()

    def mqMessage(self, routing_key, data):
        self.msg(self.channel, data['message'])

    def privmsg(self, user, channel, msg):
        user = user.split('!', 1)[0]
        if channel == self.nickname:
            # private message
            self.msg(self.channel, "let's keep it in channel, k?")
            return

        if msg.startswith(self.nickname + ":"):
            self.handle_message(user, msg[len(self.nickname)+1:].strip())

    def handle_message(self, user, msg):
        self.highscore.mq.produce(
                'irc.incoming', dict(message=msg, user=user))
