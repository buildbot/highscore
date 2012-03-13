from twisted.application import service
from highscore.app import Highscore

application = service.Application('highscore')
h = Highscore(dict(
))
h.setServiceParent(application)
