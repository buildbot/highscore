from twisted.application import service
from highscore.app import Highscore

application = service.Application('highscore')
h = Highscore(dict(
    plugins=dict(
        irc=dict(
            hostname='chat.freenode.net',
            nickname='hallmonitor',
            channel='##buildbot',
            announce=[
                'points',
                'leader',
                'github.*',
            ],
        )
    ),
    mq=dict(
        debug=True,
    ),
    www=dict(
        port=8010,
    ),
))
h.setServiceParent(application)
