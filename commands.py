__author__ = 'Andrew'

from twisted.protocols import amp
from twisted.protocols.amp import String


class SupCommand(amp.Command):
    pass


class ircSendLine(amp.Command):
    """Needs to support unicode later"""
    arguments = [('channel', String()),
                 ('message', String())]

    response = []

    errors = []


class ircConnectServer(amp.Command):
    arguments = [('network', String())]

    response = []

    errors = []


class RelaySendLine(amp.Command):
    """Needs to support unicode later"""
    arguments = [('channel', String()),
                 ('user', String()),
                 ('message', String())]