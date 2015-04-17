__author__ = "Andrew Seitz"
"""
Main iirc event loop.  Hosts the relay and is responsible for launching irc modules.
"""

import sys

from twisted.internet import protocol, reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Factory
from twisted.protocols import amp
from twisted.protocols.basic import LineReceiver
from twisted.python import log

import commands
import ircclient


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

    @commands.IRCSendRelayMSGLine.responder
    def cmdIRCSendRelayMSGLine(self, server, channel, user, message):
        user = user.split('!', 1)[0]

        line = 'msg {0} {1} {2} {3}'.format(server, channel, user, message)
        self.ampFactory.getRelay().sendLine(line)
        return {}

    @commands.IRCSendRelayInfoLine.responder
    def cmdIRCSendRelayInfoLine(self, message):
        self.ampFactory.getRelay().sendLine(message)
        return {}

    def connectionMade(self):
        self.ampFactory.setAMP(self)
        log.msg('Connection with amp server made, proto: ', self.ampFactory.getAMP())

    def connectionLost(self, reason):
        log.msg('AMP client disconnected')
        # tear everything down


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
        self.sendLine('Type \'connect <server> <port>\' to join a server')

    def connectionLost(self, reason):
        log.msg('Relay server lost connection with client: ', reason)

    def lineReceived(self, line):
        # When a line is received from the client
        cmd = line.split(' ', 1)
        if cmd[0] == 'cmd':
            log.msg('Command received: ', cmd[1])

        elif cmd[0] == 'connect':
            # Syntax: connect <server> <nickname> <port>
            args = cmd[1].split(' ', 2)
            server = args[0]
            nickname = args[1]
            port = int(args[2])
            log.msg('Connecting to server: ' + args[0])
            # Launch the irc client module here
            ircclient.launchIRC(server, nickname, port)

        elif cmd[0] == 'sendLine':
            # Send a line to the irc server and channel
            # sendLine <server> <channel> <nickname> <message>
            args = cmd[1].split(' ', 3)
            d = self.relayFactory.getAMP().callRemote(
                commands.IRCSendLine,
                server=args[0],
                channel=args[1],
                message=args[3])
            d.addCallback(lambda l: log.msg('sendLine sent line: ', cmd[1]))

        elif cmd[0] == 'join':
            # TODO: Add the server identifier, then make the responder handle it
            # Tell the irc client to join a new channel
            args = cmd[1].split(' ', 2)
            log.msg('Join command: ', args)
            d = self.relayFactory.getAMP().callRemote(
                commands.IRCJoinChannel,
                server=args[0],
                channel=args[1])
            d.addCallback(lambda l: log.msg('Join channel ',  args))

        elif cmd[0] == 'part':
            # Tell the irc client to leave a channel
            args = cmd[1].split(' ')
            argLength = len(args)
            if argLength == 1:
                reason = ''
            else:
                reason = args[1]

            if argLength < 2:
                self.relayFactory.getAMP().callRemote(
                    commands.IRCLeaveChannel,
                    channel=args[0],
                    reason=reason)
            else:
                self.sendLine('Error: bad command: ' + cmd[0] + ' ' + cmd[1])

        elif cmd[0] == 'disconnect':
            # Kill the irc module
            log.msg('disconnect received')

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


def startIIRC():
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

    # reactor.run()