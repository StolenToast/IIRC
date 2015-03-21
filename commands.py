__author__ = 'Andrew'

from twisted.protocols import amp
from twisted.protocols.amp import String, Integer


class SupCommand(amp.Command):
    pass


class IRCSendLine(amp.Command):
    """Needs to support unicode later"""
    arguments = [('channel', String()),
                 ('message', String())]

    response = []

    errors = []


class IRCJoinChannel(amp.Command):
    arguments = [('channel', String())]
    response = []
    errors = []


class IRCLeaveChannel(amp.Command):
    arguments = [('channel', String()),
                 ('reason', String())]
    response = []
    errors = []


class IRCConnectServer(amp.Command):
    arguments = [('network', String()),
                 ('port', Integer())]

    response = []

    errors = []


class IRCSendRelayLine(amp.Command):
    """Needs to support unicode later"""
    arguments = [('channel', String()),
                 ('user', String()),
                 ('message', String())]