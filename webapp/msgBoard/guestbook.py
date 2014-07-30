# -*- coding: utf-8 -*-
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb


import logging
import webapp2
import jinja2
import facebook

from webapp2_extras import sessions
from wtforms import Form, StringField, TextAreaField, validators

config = {}
config['webapp2_extras.sessions'] = dict(secret_key='')

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

DEFAULT_GUESTBOOK_NAME = 'default_guestbook'
RESTRICTED_WORDS = [u'天安門', u'台獨']

FACEBOOK_APP_ID = "498674806942717"
FACEBOOK_APP_SECRET = "9b0b204fca2f08f1f3d19a41ee8b9eaf"

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

class BaseHandler(webapp2.RequestHandler):

    """Provides access to the active Facebook user in self.current_user

    The property is lazy-loaded on first access, using the cookie saved
    by the Facebook JavaScript SDK to determine the user ID of the active
    user. See http://developers.facebook.com/docs/authentication/ for
    more information.
    """
    def current_user(self):
        if self.session.get("user"):
            # User is logged in
            return self.session.get("user")
        elif users.get_current_user():
            current_user = users.get_current_user()
            user = dict(
                    id=current_user.user_id(),
                    nickname=current_user.nickname(),
                    profile_url="",
                    access_token="",
                    is_google=True
                )
            # User is now logged in
            self.session["user"] = user
            return self.session.get("user")
        else:
            # Either used just logged in or just saw the first page
            # We'll see here
            cookie = facebook.get_user_from_cookie(self.request.cookies,
                                                   FACEBOOK_APP_ID,
                                                   FACEBOOK_APP_SECRET)
            if cookie:
                # Not an existing user so get user info
                graph = facebook.GraphAPI(cookie["access_token"])
                profile = graph.get_object("me")
                user = dict(
                    id=str(profile["id"]),
                    nickname=profile["name"],
                    profile_url=profile["link"],
                    access_token=cookie["access_token"],
                    is_google=False
                )
                # User is now logged in
                self.session["user"] = user
                return self.session.get("user")
        return None

    def dispatch(self):
        """
        This snippet of code is taken from the webapp2 framework documentation.
        See more at
        http://webapp-improved.appspot.com/api/webapp2_extras/sessions.html

        """
        self.session_store = sessions.get_store(request=self.request)
        try:
            webapp2.RequestHandler.dispatch(self)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        """
        This snippet of code is taken from the webapp2 framework documentation.
        See more at
        http://webapp-improved.appspot.com/api/webapp2_extras/sessions.html

        """
        return self.session_store.get_session()

class MainPage(BaseHandler):
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

        current_user = self.current_user()

        logging.info(current_user)

        if current_user:
            url = users.create_logout_url(self.request.host_url + '/login')
            usr_login = True
        else:
            url = self.request.host_url + '/login'
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

            if self.current_user():
                greeting.author = self.current_user()

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
        book_form = ChangeGuestBookForm(self.request.POST)

        if book_form.validate():
            query_params = {'guestbook_name': book_form.guestbook_name.data}
        else:
            query_params = {'guestbook_name': bookname}

        self.redirect('/?' + urllib.urlencode(query_params))

class LoginHandler(BaseHandler):
    def get(self):
        self.session["user"] = None
        template_values = {
            'facebook_app_id': FACEBOOK_APP_ID,
            'google_login': users.create_login_url(self.request.host_url),
            'url': self.request.host_url
        }

        template = JINJA_ENVIRONMENT.get_template('login.html')
        self.response.write(template.render(template_values))


application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/changebook', ChangeBookHandler),
    ('/login', LoginHandler),
], debug=True, config=config)
