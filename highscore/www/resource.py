# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

from twisted.python import log
from twisted.internet import defer
from twisted.web import resource, server

html_template = """\
<!doctype html>
<!-- paulirish.com/2008/conditional-stylesheets-vs-css-hacks-answer-neither/ -->
<!--[if lt IE 7]> <html class="no-js lt-ie9 lt-ie8 lt-ie7" lang="en"> <![endif]-->
<!--[if IE 7]>    <html class="no-js lt-ie9 lt-ie8" lang="en"> <![endif]-->
<!--[if IE 8]>    <html class="no-js lt-ie9" lang="en"> <![endif]-->
<!-- Consider adding a manifest.appcache: h5bp.com/d/Offline -->
<!--[if gt IE 8]><!--> <html class="no-js" lang="en"> <!--<![endif]-->
<head>
  <meta charset="utf-8">

  <!-- Use the .htaccess and remove these lines to avoid edge case issues.
       More info: h5bp.com/i/378 -->
  <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">

  <title></title>
  <meta name="description" content="High Scores">

  <!-- Mobile viewport optimized: h5bp.com/viewport -->
  <meta name="viewport" content="width=device-width">

  <link rel="stylesheet" href="css/style.css">

</head>
<body>
  <!-- Prompt IE 6 users to install Chrome Frame. Remove this if you support IE 6.
       chromium.org/developers/how-tos/chrome-frame-getting-started -->
  <!--[if lt IE 7]><p class=chromeframe>Your browser is <em>ancient!</em> <a href="http://browsehappy.com/">Upgrade to a different browser</a> or <a href="http://www.google.com/chromeframe/?redirect=true">install Google Chrome Frame</a> to experience this site.</p><![endif]-->
  <header>

  </header>
  <div role="main">
%(content)s
  </div>
  <footer>

  </footer>


  <!-- JavaScript at the bottom for fast page loading -->
</body>
</html>
"""

class Resource(resource.Resource):

    contentType = 'text/html'

    def __init__(self, highscore):
        resource.Resource.__init__(self)
        self.highscore = highscore

    def render(self, request):
        d = defer.maybeDeferred(lambda : self.content(request))
        def handle(data):
            if isinstance(data, unicode):
                data = data.encode("utf-8")
            request.setHeader("content-type", self.contentType)
            if request.method == "HEAD":
                request.setHeader("content-length", len(data))
                return ''
            return data
        d.addCallback(handle)
        def ok(data):
            request.write(data)
            try:
                request.finish()
            except RuntimeError:
                # this occurs when the client has already disconnected; ignore
                # it (see #2027)
                log.msg("http client disconnected before results were sent")
        def fail(f):
            request.processingFailed(f)
            return None # processingFailed will log this for us
        d.addCallbacks(ok, fail)
        return server.NOT_DONE_YET


class HighscoreResource(Resource):

    @defer.inlineCallbacks
    def content(self, request):
        high_scores = yield self.highscore.points.getHighscores()

        scores_html = []
        for sc in high_scores:
            scores_html.append('<li>%s (%d points)' %
                    (sc['display_name'], round(0.5 + sc['points'])))
        content = "<ul>%s</ul>" % ("\n".join(scores_html),)
        defer.returnValue(html_template % dict(content=content))
