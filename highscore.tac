from twisted.application import service
from highscore.app import Highscore
from highscore.local import MySQLConfig 

application = service.Application('highscore')
h = Highscore(dict(
    basedir="/home/cc/bbprojs/bb_highscores/highscore",
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
    db=dict(
          url="mysql://%s:%s@localhost/highscore" %
               (MySQLConfig.MYSQL_USER, MySQLConfig.MYSQL_PASSWORD),
    ),
    mq=dict(
        debug=True,
    ),
    www=dict(
        port=8010,
    ),
))
h.setServiceParent(application)
