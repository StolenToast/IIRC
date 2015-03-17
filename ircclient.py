__author__ = "Andrew"
import sys

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.python import log


"""Need to get all the commands"""
import commands


class IRCConnection(irc.IRCClient):
    nickname = "twisted_toast"

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        log.msg('Connection succeeded')

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        print('connection lost')

    def signedOn(self):
        """When the client has signed on to the server"""
        self.join(self.factory.channel)

    def joined(self, channel):
        """When the client joins a channel"""
        print('join: ' + channel)
        d = self.amp.callRemote(commands.SupCommand)
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


class IRCConnectionFactory(protocol.ClientFactory):
    def __init__(self, channel, ampclient):
        self.channel = channel
        self.amp = ampclient
        log.msg('irc factory init run')

    def buildProtocol(self, addr):
        ircc = IRCConnection()
        ircc.factory = self
        ircc.amp = self.amp
        log.msg('Client has been set up')
        return ircc

    def clientConnectionLost(self, connector, reason):
        log.msg('A client lost connection: ', reason)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        log.msg('A client connection failed: ', reason)
        reactor.stop()


class AMPClient(commands.amp.AMP):
    def connectionMade(self):
        log.msg("AMP has connected")

    def connectionLost(self, reason):
        log.msg('AMP has disconnected')


class AMPClientFactory(protocol.ClientFactory):
    protocol = AMPClient
    log.msg("New amp protocol spawned")

    def buildProtocol(self, addr):
        ampclient = AMPClient()
        log.msg('ampclient spawned')
        return ampclient


class AMPServer(commands.amp.AMP):
    @commands.SupCommand.responder
    def sup(self):
        log.msg('got SupCommand')
        return {}


class AMPServerFactory(protocol.ServerFactory):
    protocol = AMPServer


if __name__ == '__main__':
    log.startLogging(sys.stdout)

    def gotAmpClient(amp):
        """ Set up the IRC connection"""
        ircfactory = IRCConnectionFactory(channel='#secretfun', ampclient=amp)
        server = "irc.freenode.net"
        reactor.connectTCP(server, 6667, ircfactory)
        log.msg("IRC Client connected")

    """Set up the AMP connection"""
    point = TCP4ClientEndpoint(reactor, 'localhost', 9992)
    d = connectProtocol(point, AMPClient())
    d.addCallback(gotAmpClient)
    # reactor.connectTCP('localhost', 9992, ampclient)
    # log.msg("AMP has attempted to connect as a client")

    reactor.run()