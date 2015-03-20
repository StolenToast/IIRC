import sys

from twisted.internet import protocol, reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Factory
from twisted.protocols import amp
from twisted.protocols.basic import LineReceiver
from twisted.python import log

import commands


class SupCommand(amp.Command):
    pass


class AMPProtocol(amp.AMP):
    """Needs reference to own factory"""

    def __init__(self):
        self.ampFactory = None

    @commands.SupCommand.responder
    def sup(self):
        log.msg('got sup')
        return {}

    @commands.RelaySendLine.responder
    def cmdSendRelayLine(self, channel, user, message):
        self.ampFactory.getRelay().sendLine(channel + ',' + user + ': ' + message)
        return {}

    def connectionMade(self):
        self.ampFactory.setAMP(self)
        log.msg('Connection with amp server made, proto: ', self.ampFactory.getAMP())

    def connectionLost(self, reason):
        log.msg('AMP client disconnected')


class AMPFactory(protocol.ServerFactory):
    protocol = AMPProtocol

    """Needs a reference to its current AMP and the Relay factory"""

    def __init__(self):
        self.amp = None
        self.relayFactory = None

    def buildProtocol(self, addr):
        self.amp = AMPProtocol()
        self.amp.ampFactory = self
        log.msg('AMP client spawned')
        return self.amp

    def getAMP(self):
        return self.amp

    def setAMP(self, ap):
        self.amp = ap

    def getRelay(self):
        return self.relayFactory.getRelay()

    def setRelayFactory(self, rf):
        self.relayFactory = rf

    def getRelayFactory(self):
        return self.relayFactory


class RelayProtocol(LineReceiver):
    def __init__(self):
        # self.relayFactory = rf
        # self.relayFactory.setRelay(self)
        self.relayFactory = None

    """Wants a reference to its factory"""

    def connectionMade(self):
        self.relayFactory.setRelay(self)
        self.sendLine('Welcome to iirc')
        c = self.relayFactory.getAMP().callRemote(SupCommand)
        # c = self.relayFactory.sendAMP(SupCommand)
        c.addCallback(lambda l: log.msg('successful AMP command by server')).addErrback(
            lambda e: log.msg('Error occured at A'))

    def connectionLost(self, reason):
        log.msg('Relay server lost connection with client: ', reason)

    def lineReceived(self, line):
        """When a line is received from the client"""
        cmd = line.split(' ', 1)
        if cmd[0] == 'cmd':
            log.msg('Command received: ', cmd[1])

        elif cmd[0] == 'connect':
            args = cmd[1]
            log.msg('Connecting to server: ' + args)
            d = self.relayFactory.getAMP().callRemote(
                commands.ircConnectServer,
                network=args)
            d.addCallback(lambda l: log.msg('Connected to ' + args))

        elif cmd[0] == 'sendLine':
            """Send a line to the irc server and channel"""
            args = cmd[1].split(' ', 1)
            d = self.relayFactory.getAMP().callRemote(
                commands.ircSendLine,
                channel=args[0],
                message=args[1])
            d.addCallback(lambda l: log.msg('successfully sent a message'))

        else:
            log.msg(cmd)


class RelayFactory(Factory):
    protocol = RelayProtocol

    def __init__(self):
        """Needs reference to current Relay and the AMP Factory"""
        self.relay = None
        self.ampFactory = None

    # def sendAMP(self, arg):
    # self.ampFactory.amp.callRemote(arg)

    def getRelay(self):
        return self.relay

    def setRelay(self, rl):
        self.relay = rl

    def getAMP(self):
        return self.ampFactory.getAMP()

    def setAMPFactory(self, af):
        self.ampFactory = af

    def getAMPFactory(self):
        return self.ampFactory

    def startedConnecting(self, connector):
        log.msg('Main server line receiver connecting...')

    def buildProtocol(self, addr):
        log.msg('Main server line receiver connected!')
        self.relay = RelayProtocol()
        self.relay.relayFactory = self
        return self.relay


log.startLogging(sys.stdout)

"""Start the AMP server"""
amppoint = TCP4ServerEndpoint(reactor, 9992)
ampfactory = AMPFactory()
amppoint.listen(ampfactory)

log.msg("AMP server started")

"""Start the Relay server"""
relaypoint = TCP4ServerEndpoint(reactor, 9993)
relayfactory = RelayFactory()
relaypoint.listen(relayfactory)

relayfactory.setAMPFactory(ampfactory)
ampfactory.setRelayFactory(relayfactory)

log.msg('relayFactory.ampFactory: ', relayfactory.getAMPFactory())
log.msg('ampFactory.relayFactory: ', ampfactory.getRelayFactory())

# log.msg('relayFactory reference to amp: ', relayFactory.getAMP())
# log.msg('ampFactory reference to relay: ', ampFactory.getRelay())

reactor.run()