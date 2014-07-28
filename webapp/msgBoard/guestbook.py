# -*- coding: utf-8 -*-
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import logging
import webapp2
import jinja2
import facebook

from wtforms import Form, StringField, TextAreaField, validators


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

DEFAULT_GUESTBOOK_NAME = 'default_guestbook'
RESTRICTED_WORDS = [u'天安門', u'台獨']

FACEBOOK_APP_ID = "your app id"
FACEBOOK_APP_SECRET = "your app secret"

class TextInputForm(Form):
    inputstring = TextAreaField('Inputstring', [validators.InputRequired()])

class ChangeGuestBookForm(Form):
    guestbook_name = StringField('guestbook_name',
                           [validators.InputRequired(), validators.AnyOf(['default_guestbook','guestbook3'], message="Invalid book")],
                           default=u'default_guestbook')

# We set a parent key on the 'Greetings' to ensure that they are all in the same
# entity group. Queries across the single entity group will be consistent.
# However, the write rate should be limited to ~1/second.

def guestbook_key(guestbook_name=DEFAULT_GUESTBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity with guestbook_name."""
    return ndb.Key('Guestbook', guestbook_name)

class Greeting(ndb.Model):
    """Models an individual Guestbook entry."""
    author = ndb.UserProperty()
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    warning = ndb.BooleanProperty()

class MainPage(webapp2.RequestHandler):
    def get(self):
        text_form = TextInputForm()
        book_form = ChangeGuestBookForm()
        
        guestbook_name = self.request.get('guestbook_name',
                                    DEFAULT_GUESTBOOK_NAME)

        book_form.guestbook_name.data = guestbook_name
        # Ancestor Queries, as shown here, are strongly consistent with the High
        # Replication Datastore. Queries that span entity groups are eventually
        # consistent. If we omitted the ancestor from this query there would be
        # a slight chance that Greeting that had just been written would not
        # show up in a query.
        greetings_query = Greeting.query(
            ancestor=guestbook_key(guestbook_name)).order(-Greeting.date)
        greetings = greetings_query.fetch(10)
        greetings.reverse()

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            usr_login = True
        else:
            url = users.create_login_url(self.request.uri)
            usr_login = False

        if len(greetings) > 0:
            do_warning = greetings[0].warning
        else:
            do_warning = False

        template_values = {
            'greetings': greetings,
            'guestbook_name': guestbook_name,
            'url': url,
            'usr_login': usr_login,
            'do_warning': do_warning,
            'text_form': text_form,
            'book_form': book_form
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))

    def post(self):
        # We set the same parent key on the 'Greeting' to ensure each Greeting
        # is in the same entity group. Queries across the single entity group
        # will be consistent. However, the write rate to a single entity group
        # should be limited to ~1/second.
        bookname = self.request.get('guestbook_name')
        text_form = TextInputForm(self.request.POST)

        if text_form.validate():
            greeting = Greeting(parent=guestbook_key(bookname))

            if users.get_current_user():
                greeting.author = users.get_current_user()

            greeting.content = text_form.inputstring.data
            warning = False
            for word in RESTRICTED_WORDS:
                warning |= (greeting.content.find(word) != -1)
            greeting.warning = warning
            greeting.put()

        query_params = {'guestbook_name': bookname}
        self.redirect('/?' + urllib.urlencode(query_params))

class ChangeBookHandler(webapp2.RequestHandler):
    def post(self):
        bookname = self.request.get('guestbook_name')
        logging.info("=====%s======" % bookname)
        book_form = ChangeGuestBookForm(self.request.POST)

        if book_form.validate():
            query_params = {'guestbook_name': book_form.guestbook_name.data}
        else:
            query_params = {'guestbook_name': bookname}

        self.redirect('/?' + urllib.urlencode(query_params))

class LoginHandler(webapp2.RequestHandler):
    def get(self):
        pass
    def post(self):
        self.redirect('/')


application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/changebook', ChangeBookHandler),
    ('/login', LoginHandler),
], debug=True)