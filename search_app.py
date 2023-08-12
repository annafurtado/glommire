# -*- coding: utf-8 -*-
#!/usr/bin/python

from cgi import parse_qs
from datetime import datetime
import os
import string
import urllib
from urlparse import urlparse
import yaml
import glob
import logging

import reader

import webapp2
from webapp2_extras import jinja2

from google.appengine.api import search
from google.appengine.api import users

_INDEX_NAME = 'UTE'

class BaseHandler(webapp2.RequestHandler):
    """
    The other handlers inherit from this class.  Provides some helper
    methods for rendering a template.
    """

    @webapp2.cached_property
    def jinja2(self):
      return jinja2.get_jinja2(app=self.app)

    def render_template(self, filename, template_args):
      self.response.write(self.jinja2.render_template(filename, **template_args))


class MainPage(BaseHandler):
    """Handles search requests for comments."""

    def get(self):
        """Handles a get request with a query."""
        req = self.request.uri
        uri = urlparse(req)

        query = ''
        queried = False
        query_obj = search.Query(query_string=query)
        if uri.query:
            query = parse_qs(uri.query)
            query = query['query'][0]
        if query:
            query_obj = search.Query(query_string=query)
            results = search.Index(name=_INDEX_NAME).search(query=query_obj)
            selection = self.select_ute_results(results, query)
            verbetes = self.make_verbetes(selection)
            queried = True
        else:
            verbetes = []

        template_values = {
            'verbetes': verbetes,
            'number_returned': len(verbetes),
            'queried': queried
			}
        self.render_template('index.html', template_values)

    def select_ute_results(self, results, query):
        '''
        :results --> list
        :query --> str

        restricts search to ute fields

        returns list of results
        '''
        my_results = []
        for r in results.results:
            for f in r.fields:
                if f.name == 'ute':
                    value = f.value
                    if query in f.value.encode('utf-8'):
                        my_results.append(r)
        return my_results

    def make_verbetes(self, results,
                      fields = ['ute', 'contexto', 'obs', 'variante',
                                'freq', 'en', 'pt', 'es', 'fr', 'uter' ]):
        '''
        :results --> list
        :fields ---> list of str (field names)
        orders fields into micro structure standard order by transforming
        result dictionaries into list of [k, v]

        discards fields having NoneType values


        TODO this function should be dismembered into two!

        returns list of results
        '''
        rdicts = []
        for r in results:
            d = {f: None for f in fields}
            for f in r.fields:
                if f.name in fields and f.value not in [None, 'None']:
                    d[f.name] = f.value
            rdicts.append(d)

        verbetes = []
        for rdict in rdicts:
            entry = []
            for f in fields:
                if rdict[f] is None:
                    continue
                elif f in ['en', 'pt', 'es', 'fr', 'ute', 'uter'] and '-dot-' not in rdict[f]:
                    rdict[f] = [rdict[f]]
                elif '-dot-' in rdict[f]:
                    rdict[f] = rdict[f].split('-dot-')
                entry.append([f, rdict[f]])
            verbetes.append(entry)
        return verbetes

    def post(self):
        """Handles a post request."""
        query = self.request.get('search')
        if query:
            self.redirect('/?' + urllib.urlencode(
                {'query': query.encode('utf8')})+'#cta')
        else:
            self.redirect('/')

def CreateDocument(**args):
    """Creates a search.Document from content written by the author."""
    # Let the search service supply the document id.
    my_fields = []
    for arg in args:
        my_fields.append(search.HtmlField(name=arg, value=args[arg]))
    my_fields.append(search.DateField(name='date', value=datetime.now().date()))
    return search.Document(fields= my_fields)

def stringfy(lista):
    '''
    :lista --> list (o valor de um campo de uma ficha)

    transforms the list in string so that it can be passed as argument
    to the function CreateDocument
    '''
    txt = ''
    if len(lista) == 1:
        if type(lista[0]) is float:
            lista[0] = str(lista[0])
        txt = lista[0]
    else:
        txt = lista[0]
        for el in lista[1:]:
            logging.info(lista[1:])
            txt += '-dot-%s'%el
    return txt

class Admin(BaseHandler):
    """builds index."""

    def get(self):
        user = users.get_current_user()
        url = users.create_login_url(self.request.uri)

        if user:
            if  users.is_current_user_admin():
                user = user.nickname
                url = users.create_logout_url(self.request.uri)
                url_linktext = 'Logout'

            else:
                self.response.out.write('acesso negado')
                self.redirect(url)
                return
            self.render_template('admin.html' ,
                        {'url': url, 'url_linktext': url_linktext,})
        else:

            self.redirect(url)


    def post(self):
            author = None

            user = users.get_current_user()
            user = user.nickname
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'

            author = users.get_current_user()
	    cria_indice = self.request.get('cria_indice')
	    deleta_indice = self.request.get('deleta_indice')
	    files = glob.glob("data/*.yaml")
	    my_index = search.Index(name=_INDEX_NAME)
	    r = my_index.get_range(ids_only = True)

	    if cria_indice:
                for f in files:
                    mup = reader.read_yaml_file(f)
                    if 'pt' not in mup:
                        my_index.put(CreateDocument(ute = stringfy(mup['UTE']),
                                                contexto = stringfy(mup['contexto']),
                                                uter = stringfy (mup['UTEs_relacionadas']),
                                                en = stringfy(mup['en']),
                                                fr = stringfy(mup['fr']),
                                                es = stringfy(mup['es']),
                                                obs = stringfy(mup['obs']),
                                                variante = stringfy(mup['variante']),
                                                freq = stringfy(mup['freq']) ) )
                    elif 'en' not in mup:

                        my_index.put(CreateDocument(ute = stringfy(mup['UTE']),
                                                contexto = stringfy(mup['contexto']),
                                                uter = stringfy (mup['UTEs_relacionadas']),
                                                pt = stringfy(mup['pt']),
                                                fr = stringfy(mup['fr']),
                                                es = stringfy(mup['es']),
                                                obs = stringfy(mup['obs']),
                                                variante = stringfy(mup['variante']),
                                                freq = stringfy(mup['freq']) ) )
                    elif 'fr' not in mup:

                        my_index.put(CreateDocument(ute = stringfy(mup['UTE']),
                                                contexto = stringfy(mup['contexto']),
                                                uter = stringfy (mup['UTEs_relacionadas']),
                                                pt = stringfy(mup['pt']),
                                                en = stringfy(mup['en']),
                                                es = stringfy(mup['es']),
                                                obs = stringfy(mup['obs']),
                                                variante = stringfy(mup['variante']),
                                                freq = stringfy(mup['freq']) ) )
                    elif 'es' not in mup:

                        my_index.put(CreateDocument(ute = stringfy(mup['UTE']),
                                                contexto = stringfy(mup['contexto']),
                                                uter = stringfy (mup['UTEs_relacionadas']),
                                                pt = stringfy(mup['pt']),
                                                fr = stringfy(mup['fr']),
                                                en = stringfy(mup['en']),
                                                obs = stringfy(mup['obs']),
                                                variante = stringfy(mup['variante']),
                                                freq = stringfy(mup['freq']) ) )
                    else:
                        raise Exception

	    elif deleta_indice:
                r = my_index.get_range(ids_only = True)
                my_ids = []

		for doc in r:
                    my_ids.append(doc.doc_id)

                my_index.delete(my_ids)
                r = my_index.get_range(ids_only = True)
                my_index.delete_schema()

            self.render_template('index.html' ,
                        {'url': url, 'url_linktext': url_linktext,})


application = webapp2.WSGIApplication(
    [('/', MainPage),
     ('/admin', Admin)],
    debug=True)
