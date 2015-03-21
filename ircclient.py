__author__ = "Andrew"
"""
This is the module that connects to the IRC server and channels.
When it is created a connection to the master's AMP server will be made and then a connection to the IRC server.  One of these should be spawned for every server that we connect to.
"""

import sys

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.python import log


"""Need to get all the commands"""
import commands


class IRCProtocol(irc.IRCClient):
    nickname = "twisted_toast"

    def __init__(self):
        self.ircFactory = None

    def connectionMade(self):
        self.ircFactory.setIRC(self)
        irc.IRCClient.connectionMade(self)
        log.msg('Connection succeeded')

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        # connector.connect()
        print('connection lost')

    def signedOn(self):
        """When the client has signed on to the server"""
        self.join(self.ircFactory.channel)

    def joined(self, channel):
        """When the client joins a channel"""
        print('join: ' + channel)
        d = self.ircFactory.getAMP().callRemote(commands.SupCommand)
        d.addCallback(lambda l: log.msg("Callback from the SupCommand"))

    def privmsg(self, user, channel, message):
        """When the client receives a privmsg line"""
        log.msg('Line received: ' + channel + ',' + user.split('!', 1)[0] + ' - ' + message)
        d = self.ircFactory.getAMP().callRemote(
            commands.IRCSendRelayLine,
            channel=channel,
            user=user,
            message=message)
        d.addCallback(lambda l: log.msg('sent line to relay'))

    def action(self, user, channel, data):
        """When an action (/me) is detected"""
        print channel, ' ', channel, ' ', data

    def irc_NICK(self, prefix, params):
        """When someone's nick is changed"""
        print prefix, ' ', params


class IRCFactory(protocol.ClientFactory):
    def __init__(self, channel):
        self.irc = None
        self.channel = channel
        self.server = None
        self.ampFactory = None
        # self.amp = ampclient
        log.msg('irc factory init run')

    def buildProtocol(self, addr):
        ircc = IRCProtocol()
        ircc.ircFactory = self
        # ircc.amp = self.amp
        log.msg('Client has been set up')
        return ircc

    def clientConnectionLost(self, connector, reason):
        log.msg('A client lost connection: ', reason)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        log.msg('A client connection failed: ', reason)
        reactor.stop()

    def setAMP(self, af):
        self.ampFactory = af

    def getAMP(self):
        return self.ampFactory.getAMP()

    def setIRC(self, irf):
        self.irc = irf

    def getIRC(self):
        return self.irc


class AMPProtocol(commands.amp.AMP):
    def __init__(self):
        self.ampFactory = None

    @commands.SupCommand.responder
    def sup(self):
        log.msg('Relay has connected to the master')
        return {}

    @commands.IRCSendLine.responder
    def cmdIRCSendLine(self, channel, message):
        """Sends a line to the connected server and specified channel
        Will only send ascii for now, need to implement unicode later"""
        log.msg('sendLine command received, ch: ' + channel + ' ms: ' + message)
        self.ampFactory.getIRC().say(channel=channel, message=message)
        return {}

    @commands.IRCConnectServer.responder
    def cmdIRCConnectServer(self, network, port):
        """Connect to the supplied server"""
        self.ampFactory.getIRC().quit()

    @commands.IRCJoinChannel.responder
    def cmdIRCJoinChannel(self, channel):
        self.ampFactory.getIRC().join(channel)
        return {}

    @commands.IRCLeaveChannel.responder
    def cmdIRCLeaveChannel(self, channel, reason):
        self.ampFactory.getIRC().leave(channel, reason)
        return {}

    def connectionMade(self):
        self.ampFactory.setAMP(self)
        log.msg("AMP has connected")

    def connectionLost(self, reason):
        log.msg('AMP has disconnected')


class AMPFactory(protocol.ClientFactory):
    protocol = AMPProtocol

    def __init__(self):
        self.amp = None
        self.ircFactory = None

    def buildProtocol(self, addr):
        self.amp = AMPProtocol()
        self.amp.ampFactory = self
        log.msg('AMP client spawned')
        return self.amp

    def getAMP(self):
        return self.amp

    def setAMP(self, ap):
        self.amp = ap

    def getIRC(self):
        return self.ircFactory.getIRC()

    def setIRC(self, irf):
        self.ircFactory = irf


if __name__ == '__main__':
    log.startLogging(sys.stdout)

    # def gotAmpClient(amp):
    # """ Set up the IRC connection"""
    # ircfactory = IRCConnectionFactory(channel='#secretfun', ampclient=amp)
    # server = "irc.freenode.net"
    # reactor.connectTCP(server, 6667, ircfactory)
    # log.msg("IRC Client connected")
    #
    # """Set up the AMP connection"""
    # point = TCP4ClientEndpoint(reactor, 'localhost', 9992)
    # d = connectProtocol(point, AMPProtocol())
    # d.addCallback(gotAmpClient)
    # reactor.connectTCP('localhost', 9992, ampclient)
    # log.msg("AMP has attempted to connect as a client")

    """Start and connect the AMP client"""
    amppoint = TCP4ClientEndpoint(reactor, 'localhost', 9992)
    ampfactory = AMPFactory()
    amppoint.connect(ampfactory)

    log.msg('AMP client connected')

    """Start and connect the IRCClient"""
    # ircpoint = TCP4ClientEndpoint(reactor, "irc.freenode.net", 6667)
    ircfactory = IRCFactory(channel='#secretfun')
    # ircpoint.connect(ircfactory)
    server = "irc.freenode.net"
    reactor.connectTCP(server, 6667, ircfactory)

    log.msg('IRC connecting to server')

    """Set factory references"""
    ampfactory.setIRC(ircfactory)
    ircfactory.setAMP(ampfactory)

    reactor.run()