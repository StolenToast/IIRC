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
        return self.relayFactory

    def setRelay(self, rf):
        self.relayFactory = rf


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
        cmd = line.split(" ", 1)
        if cmd == 'cmd':
            log.msg('Command received: ', line)
        elif cmd == 'connect':
            log.msg('Starting new connection')
        else:
            log.msg(cmd)


class RelayFactory(Factory):
    protocol = RelayProtocol

    def sendAMP(self, arg):
        self.ampFactory.amp.callRemote(arg)

    def __init__(self):
        """Needs reference to current Relay and the AMP Factory"""
        self.relay = None
        self.ampFactory = None

    def getRelay(self):
        return self.relay

    def setRelay(self, rl):
        """
        :param rl: RelayProtocol:
        :return:
        """
        self.relay = rl

    def getAMP(self):
        return self.ampFactory.amp

    def setAMP(self, af):
        self.ampFactory = af

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

relayfactory.setAMP(ampfactory)
ampfactory.setRelay(relayfactory)

log.msg('relayFactory.ampFactory: ', relayfactory.getAMP())
log.msg('ampFactory.relayFactory: ', ampfactory.getRelay())

# log.msg('relayFactory reference to amp: ', relayFactory.getAMP())
# log.msg('ampFactory reference to relay: ', ampFactory.getRelay())

reactor.run()