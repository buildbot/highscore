from twisted.application import service
from highscore.app import Highscore

application = service.Application('highscore')
h = Highscore(dict(
    plugins=dict(
        irc=dict(
            hostname='chat.freenode.net',
            nickname='hallmonitor',
            channel='##buildbot',
        )
    ),
    mq=dict(
        debug=True,
    ),
))
h.setServiceParent(application)
