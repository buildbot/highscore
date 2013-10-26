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

import time
from twisted.python import log, util
from twisted.internet import defer
from twisted.web import resource, server, template, static

from highscore.const import ConstMaster as const

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

    def content(self, request):
        return ''


class HighscoresElement(template.Element):

    loader = template.XMLFile(util.sibpath(__file__, 'templates/leaderboard.xhtml'))

    def __init__(self, highscore, scores, ltscores):
        template.Element.__init__(self)
        self.highscore = highscore
        self.scores = scores
        self.ltscores = ltscores

    @template.renderer
    def title(self, request, tag):
        return tag("High Scores")

    def getPostSuffix(self, pos):
        posDict = {1 : 'st', 2: 'nd', 3: 'rd'}
        return posDict.get(pos, 'th') 

    def getPosStr(self, position):
        return str(position) + self.getPostSuffix(position)

    def getClassCol(self, position):
        classDict = {1: 'first', 2: 'second', 3: 'third'}
        return classDict.get(position, 'others') 

    def toHref(self, row):
        url = self.highscore.www.makeUrl('user', row['userid'])
        return template.tags.a(row['display_name'],
                               class_="display_name", href=url)

    @template.renderer
    def monthly_header(self, request, tag):
        h3 = template.tags.h3('Monthly', class_='monthly')
        return h3

    @template.renderer
    def lifetime_header(self, request, tag):
        h3 = template.tags.h3(template.tags.b('Lifetime'), class_='lifetime')
        return h3

    def getTableHeader(self):
        th_pos = template.tags.th('Pos.', class_='pos_col')
        th_name = template.tags.th('Name', class_='name_col')
        th_pts  = template.tags.th('Points', class_='pts_col')
        tr = template.tags.tr(th_pos, th_name, th_pts, '')
        return tr

    @template.renderer
    def monthly_table(self, request, tag):
        position = 0
        table = template.tags.table(width='100%')
        rowlist = []
        rowlist.append(self.getTableHeader())
        for sc in self.scores:
            position += 1
 
            td_pos = template.tags.td(self.getPosStr(position),
                                      class_=self.getClassCol(position))
            td_name = template.tags.td(self.toHref(sc),
                                      class_=self.getClassCol(position))
            td_points = template.tags.td(str(sc['points']),
                                      class_=self.getClassCol(position))
            if position <= 3:
               td_excl = template.tags.td(template.tags.i("!"*(4-position)))
            else:
               td_excl = template.tags.td("")
            tr = template.tags.tr("\n", td_pos, td_name, td_points, td_excl)
            rowlist.append(tr)

        if position < 10:
           for j in range(11):
              if j > position:
                 td_pos = template.tags.td(self.getPosStr(j),
                                           class_=self.getClassCol(j))
                 td_name = template.tags.td('empty',
                                           class_=self.getClassCol(j))
                 td_points = template.tags.td('0',
                                           class_=self.getClassCol(j))
                 td_excl   = template.tags.td('')
                 tr = template.tags.tr("\n", td_pos, td_name, td_points, td_excl)
                 rowlist.append(tr)
        return template.tags.table(rowlist) 

    @template.renderer
    def lifetime_table(self, request, tag):
        position = 0
        table = template.tags.table(width='100%')
        rowlist = []
        rowlist.append(self.getTableHeader())
        for sc in self.ltscores:
            position += 1
 
            td_pos = template.tags.td(self.getPosStr(position),
                                      class_=self.getClassCol(position))
            td_name = template.tags.td(self.toHref(sc),
                                       class_=self.getClassCol(position))
            td_points = template.tags.td(str(sc['points']),
                                       class_=self.getClassCol(position))
            if position <= 3:
               td_excl = template.tags.td(template.tags.i("!"*(4-position)))
            else:
               td_excl = template.tags.td("")
            tr = template.tags.tr("\n", td_pos, td_name, td_points, td_excl)
            rowlist.append(tr)

        if position < 10:
           for j in range(11):
              if j > position:
                 td_pos = template.tags.td(self.getPosStr(j),
                                           class_=self.getClassCol(j))
                 td_name = template.tags.td('empty',
                                            class_=self.getClassCol(j))
                 td_points = template.tags.td('0',
                                            class_=self.getClassCol(j))
                 td_excl   = template.tags.td('')
                 tr = template.tags.tr("\n", td_pos, td_name, td_points, td_excl)
                 rowlist.append(tr)
        return template.tags.table(rowlist) 

class HighscoresResource(Resource):

    def __init__(self, highscore):
        Resource.__init__(self, highscore) 
        self.highscore = highscore
      
    @defer.inlineCallbacks
    def content(self, request):
        scores = yield self.highscore.points.getHighscores(const.MONTHLY_MODE)
        ltscores = yield self.highscore.points.getHighscores(const.LONGTERM_MODE)

        request.write('<!doctype html>\n')
        defer.returnValue((yield template.flattenString(request,
                                HighscoresElement(self.highscore, scores,
                                                  ltscores))))


class UsersPointsResource(Resource):

    def getChild(self, name, request):
        try:
            userid = int(name)
        except:
            return Resource.getChild(self, name, request)
        return UserPointsResource(self.highscore, userid)


class UserPointsElement(template.Element):

    loader = template.XMLFile(util.sibpath(__file__, 'templates/pointslist.xhtml'))

    def __init__(self, highscore, display_name, points):
        template.Element.__init__(self)
        self.highscore = highscore
        self.display_name = display_name
        self.points = points

    @template.renderer
    def title(self, request, tag):
        return tag("Points for %s" % (self.display_name,))

    @template.renderer
    def main_table(self, request, tag):
        ul = template.tags.ul()
        tag(ul, class_='points')
        for pt in self.points:
            li = template.tags.li()
            li(template.tags.span(
                time.asctime(time.gmtime(pt['when'])),
                class_="when"))
            li(" ")
            li(template.tags.span(
                str(pt['points']),
                class_="points"))
            li(" ")
            li(template.tags.span(
                pt['comments'],
                class_="comments"))
            ul(li)
        return ul


class UserPointsResource(Resource):

    def __init__(self, highscore, userid):
        Resource.__init__(self, highscore)
        self.highscore = highscore
        self.userid = userid

    @defer.inlineCallbacks
    def content(self, request):
        points = yield self.highscore.points.getUserPoints(self.userid)
        display_name = yield self.highscore.users.getDisplayName(self.userid)

        request.write('<!doctype html>\n')
        defer.returnValue((yield template.flattenString(request,
                                UserPointsElement(self.highscore,
                                                display_name, points))))

class PluginsResource(Resource):

    def __init__(self, highscore):
        Resource.__init__(self, highscore)
        self.highscore = highscore

    def getChild(self, name, request):
        if name in self.highscore.plugins:
            plugin = self.highscore.plugins[name]
            if plugin.www:
                return plugin.www
        return Resource.getChild(self, name, request)
