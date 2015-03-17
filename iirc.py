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


def gotAmpServer(amp):
    # global ampServer
    # ampServer = amp
    return amp


def gotRelayServer(relay):
    # global relayServer
    # relayServer = relay
    return relay


class AMPProtocol(amp.AMP):
    """Needs reference to own factory"""

    def __init__(self):
        self.ampFactory = None

    @commands.SupCommand.responder
    def sup(self):
        log.msg('got sup')
        return {}

        # def setRelay(self, relay):
        # self.relay = relay

    def connectionMade(self):
        self.ampFactory.setAMP(self)
        log.msg('Connection with amp server made, proto: ', self.ampFactory.getAMP())


class AMPFactory(protocol.ServerFactory):
    protocol = AMPProtocol

    """Needs a reference to its current AMP and the Relay factory"""

    def __init__(self):
        self.amp = None
        # self.relayFactory = None

    def setRelayFactory(self, rf):
        self.relayFactory = rf

    def getRelay(self):
        return self.relayFactory

    def buildProtocol(self, addr):
        self.amp = AMPProtocol()
        self.amp.ampFactory = self
        return self.amp

    def getAMP(self):
        return self.amp

    def setAMP(self, ap):
        self.amp = ap


class RelayProtocol(LineReceiver):
    def __init__(self, rf):
        self.relayFactory = rf
        self.relayFactory.setRelay(self)

    """Wants a reference to its factory"""

    def lineReceived(self, line):
        """When a line is received from the client"""
        cmd = line.split(" ", 1)
        if cmd == 'cmd':
            log.msg('Command received: ', line)
        elif cmd == 'connect':
            log.msg('Starting new connection')
        else:
            log.msg(cmd)

    def connectionMade(self):
        self.relayFactory.setRelay(self)
        self.sendLine('Welcome to iirc')
        c = self.relayFactory.getAMP().callRemote(SupCommand)
        # c = self.relayFactory.sendAMP(SupCommand)
        c.addCallback(lambda l: log.msg('successful AMP command by server')).addErrback(
            lambda e: log.msg('Error occured at A'))

    def connectionLost(self, reason):
        log.msg('Relay server lost connection with client: ', reason)


class RelayFactory(Factory):
    protocol = RelayProtocol

    def sendAMP(self, arg):
        self.ampFactory.amp.callRemote(arg)

    def __init__(self):
        """Needs reference to current Relay and the AMP Factory"""
        # self.relay = None
        # self.ampFactory = None

    def setAmpFactory(self, af):
        self.ampFactory = af

    def setRelay(self, rl):
        """
        :param rl: RelayProtocol:
        :return:
        """
        self.relay = rl

    def getRelay(self):
        return self.relay

    def getAMP(self):
        return self.ampFactory.amp

    def startedConnecting(self, connector):
        log.msg('Main server line receiver connecting...')

    def buildProtocol(self, addr):
        log.msg('Main server line receiver connected!')
        relay = RelayProtocol(self)
        self.relay.relayFactory = self
        return self.relay


log.startLogging(sys.stdout)

"""Start the AMP server"""
# reactor.listenTCP(9992, AMPServerFactory())
# ampDeferred = amppoint.listen(AMPFactory())
# ampDeferred.addCallback(gotAmpServer)
amppoint = TCP4ServerEndpoint(reactor, 9992)
ampFactory = AMPFactory()
amppoint.listen(ampFactory)

log.msg("AMP server started")

"""Start the Relay server"""
relaypoint = TCP4ServerEndpoint(reactor, 9993)
relayFactory = RelayFactory()
relaypoint.listen(relayFactory)
# relayDeferred = relaypoint.listen(RelayFactory())
# relayDeferred.addCallback(gotRelayServer)

# ampFactory.setRelayFactory(relayFactory)
# relayFactory.setAmpFactory(ampFactory)


# def start(result):
# ampResult = result[0]
# relayResult = result[1]
#
# # Give the AMP a ref to the Relay
# ampResult.relay = relayResult
# log.msg('AMP\'s relay: ', ampResult.relay)
#
# # Give the Relay a ref to the Amp
# relayResult.amp = ampResult


# deferredList = [ampDeferred, relayDeferred]
# connectProtocols = defer.gatherResults(deferredList)
# connectProtocols.addCallback(start)

# reactor.listenTCP(9993, relayFactory)
# log.msg('Relay server has started')
#
# ampFactory = AMPFactory()
# reactor.listenTCP(9992, ampFactory)
# log.msg('AMP has started')

relayFactory.setAmpFactory(ampFactory)
ampFactory.setRelayFactory(relayFactory)

log.msg('relayFactory.ampFactory: ', relayFactory.getAMP())
log.msg('ampFactory.relayFactory: ', ampFactory.getRelay())

# log.msg('relayFactory reference to amp: ', relayFactory.getAMP())
# log.msg('ampFactory reference to relay: ', ampFactory.getRelay())

reactor.run()