__author__ = "Andrew"
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
        self.ircFactory
        irc.IRCClient.connectionMade(self)
        log.msg('Connection succeeded')

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
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
        print channel, ' ', user, ' ', message

    def action(self, user, channel, data):
        """When an action (/me) is detected"""
        print channel, ' ', channel, ' ', data

    def irc_NICK(self, prefix, params):
        """When someone's nick is changed"""
        print prefix, ' ', params


class IRCFactory(protocol.ClientFactory):
    def __init__(self, channel):
        self.channel = channel
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


class AMPProtocol(commands.amp.AMP):
    def __init__(self):
        self.ampFactory = None

    @commands.SupCommand.responder
    def sup(self):
        log.msg('Relay has connected to the master')
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
        return self.ircFactory

    def setIRC(self, irf):
        self.ircFactory = irf


if __name__ == '__main__':
    log.startLogging(sys.stdout)

    # def gotAmpClient(amp):
    # """ Set up the IRC connection"""
    # ircfactory = IRCConnectionFactory(channel='#secretfun', ampclient=amp)
    # server = "irc.freenode.net"
    # reactor.connectTCP(server, 6667, ircfactory)
    #     log.msg("IRC Client connected")
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