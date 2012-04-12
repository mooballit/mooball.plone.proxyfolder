from five import grok
from plone.dexterity.content import Item
from plone.directives import form
from zope import schema
from zope.interface import Interface, implements
from zope.location.interfaces import ILocation
import OFS.SimpleItem
import z3c.traverser.interfaces
import zope.component
import zope.publisher.interfaces
from pyquery import PyQuery as pq
import urllib2


class IProxyFolder(form.Schema):
    title = schema.TextLine(title=u'Title')
    base_url = schema.TextLine(title=u'Base URL')


class ProxyTraverser(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        view = zope.component.queryMultiAdapter(
            (self.context, self.request), name=name)
        if view is not None:
            return view
        elif hasattr(self.context, name):
            return getattr(self.context, name)

        # Check if this is the first step in the traversal
        if 'cur_proxy_path' not in self.request:
            # Check if there is actually a base_url set.
            if not self.context.base_url:
                raise zope.publisher.interfaces.NotFound(
                    self.context, name, self.request)

            # Start storing the current path in the request
            # And strip any trailing slashes
            if self.context.base_url.endswith( '/' ):
                self.context.base_url = self.context.base_url[:-1]
            
            self.request['cur_proxy_path'] = [ self.context.base_url ]
        
        self.request['cur_proxy_path'].append( name )
        
        proxy = Proxyer(self.request['cur_proxy_path'])
        #proxy.__parent__ = self.context
        return proxy #.__of__(self.context)

class IProxyer( Interface ):
    pass

class Proxyer(OFS.SimpleItem.SimpleItem):
    implements(IProxyer)
    __parent__ = None

    def __init__(self, cur_url):
        self.cur_url = cur_url
        
    def get_url( self ):
        url = '/'.join( self.cur_url )
        print 'Fetching %s' % url

        # Need to do type testing of returned data
        con = urllib2.urlopen( url )
        
        info = con.info()
        
        #if info['Content-type'] == 'text/html':
        #    # Rewrite any URLs
            
        #    # Grab content (optional?)

        return con.read()
    
    def __call__( self ):
        return self.get_url()
