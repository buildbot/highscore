from twisted.application import service
from highscore.app import Highscore
from highscore.local import MySQLConfig 

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
    mysql=dict(
          user=MySQLConfig.MYSQL_USER,
          password=MySQLConfig.MYSQL_PASSWORD,
          db_url="mysql://localhost/highscore",
    ),
    mq=dict(
        debug=True,
    ),
    www=dict(
        port=8010,
    ),
))
h.setServiceParent(application)
