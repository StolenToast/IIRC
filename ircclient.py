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

    def __init__(self, nickname, server):
        self.ircFactory = None
        self.nickname = nickname
        self.serverName = server

    def sendInfoMSG(self, message):
        self.ircFactory.getAMP().callRemote(
            commands.IRCSendRelayInfoLine,
            message=message)

    def connectionMade(self):
        self.ircFactory.setIRC(self)
        irc.IRCClient.connectionMade(self)
        log.msg('ircc: Connection succeeded')
        # self.ircFactory.getAMP().callRemote(
        # commands.IRCSendRelayInfoLine,
        # message='Connected to server, signing on...')
        self.sendInfoMSG('Connected to server, signing on...')

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        # connector.connect()
        print('connection lost')

    def signedOn(self):
        """When the client has signed on to the server"""
        self.sendInfoMSG('Signed on!  Type \'/join <channel>\' to join a channel')
        # self.join(self.ircFactory.channel)

    def joined(self, channel):
        """When the client joins a channel"""
        self.sendInfoMSG('Joined ' + channel + '!')

    def privmsg(self, user, channel, message):
        """When the client receives a privmsg line"""
        log.msg('Line Received: ' + channel + ',' + user.split('!', 1)[0] + ' - ' + message)
        d = self.ircFactory.getAMP().callRemote(
            commands.IRCSendRelayMSGLine,
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
    def __init__(self, nickname, serverName):
        self.irc = None
        # self.channel = channel
        self.nickname = nickname
        self.server = serverName
        self.ampFactory = None
        # self.amp = ampclient
        log.msg('irc factory init run')

    def buildProtocol(self, addr):
        ircc = IRCProtocol(self.nickname, self.server)
        ircc.ircFactory = self
        # ircc.amp = self.amp
        log.msg('ircc: IRC Client launched, now connecting...')
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

    def sendInfoMSG(self, message):
        self.callRemote(
            commands.IRCSendRelayInfoLine,
            message=message)

    @commands.SupCommand.responder
    def sup(self):
        log.msg('Relay has connected to the master')
        return {}

    @commands.IRCSendLine.responder
    def cmdIRCSendLine(self, server, channel, message):
        """Sends a line to the connected server and specified channel
        Will only send ascii for now, need to implement unicode later"""
        if server == self.ampFactory.getIRC().serverName:
            log.msg('sendLine command received, ch: ' + channel + ' ms: ' + message)
            self.ampFactory.getIRC().say(channel=channel, message=message)
        return {}

    @commands.IRCConnectServer.responder
    def cmdIRCConnectServer(self, network, port):
        """Connect to the supplied server"""
        self.ampFactory.getIRC().quit()

    @commands.IRCJoinChannel.responder
    def cmdIRCJoinChannel(self, server, channel):
        if server == self.ampFactory.getIRC().serverName:
            self.sendInfoMSG('joining ' + channel + '...')
            self.ampFactory.getIRC().join(channel)
        return {}

    @commands.IRCLeaveChannel.responder
    def cmdIRCLeaveChannel(self, channel, reason):
        self.ampFactory.getIRC().leave(channel, reason)
        return {'channel': channel}

    def connectionMade(self):
        self.ampFactory.setAMP(self)
        log.msg("AMP has connected")

    def connectionLost(self, reason):
        log.msg('AMP has disconnected')
        # Tear everything down
        self.ampFactory.getIRC().quit()


class AMPFactory(protocol.ClientFactory):
    protocol = AMPProtocol

    def __init__(self):
        self.amp = None
        self.ircFactory = None

    def buildProtocol(self, addr):
        self.amp = AMPProtocol()
        self.amp.ampFactory = self
        log.msg('ircc: AMP client spawned')
        return self.amp

    def getAMP(self):
        return self.amp

    def setAMP(self, ap):
        self.amp = ap

    def getIRC(self):
        return self.ircFactory.getIRC()

    def setIRC(self, irf):
        self.ircFactory = irf


def launchIRC(server, nickname, port):
    log.startLogging(sys.stdout)

    """Start and connect the AMP client"""
    amppoint = TCP4ClientEndpoint(reactor, 'localhost', 9992)
    ampfactory = AMPFactory()
    amppoint.connect(ampfactory)

    log.msg('ircc: AMP client connected')

    """Start and connect the IRCClient"""
    ircfactory = IRCFactory(nickname, server)
    reactor.connectTCP(server, port, ircfactory)

    log.msg('ircc: IRC connecting to server ' + server + ':', port)

    """Set factory references"""
    ampfactory.setIRC(ircfactory)
    ircfactory.setAMP(ampfactory)

    # reactor.run()
