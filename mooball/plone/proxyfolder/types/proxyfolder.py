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
import urllib2, urlparse


class IProxyFolder(form.Schema):
    title = schema.TextLine(title=u'Title')
    base_url = schema.TextLine(title=u'Base URL')


class ProxyFolder( Item ):
    def __call__( self ):
        return 'aaaa'

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
        if 'cur_remote_path' not in self.request:
            # Check if there is actually a base_url set.
            if not self.context.base_url:
                raise zope.publisher.interfaces.NotFound(
                    self.context, name, self.request)

            # Start storing the current path in the request
            # And strip any trailing slashes
            if self.context.base_url.endswith( '/' ):
                self.context.base_url = self.context.base_url[:-1]
            
            self.request['cur_remote_path'] = [ self.context.base_url ]
            self.request['proxy_folder_path'] = self.context.absolute_url()
        
        self.request['cur_remote_path'].append( name )
        
        proxy = Proxyer(self.request, self.request['cur_remote_path'],self.request['proxy_folder_path'])
        #proxy.__parent__ = self.context
        return proxy #.__of__(self.context)

class IProxyer( Interface ):
    pass

class Proxyer(OFS.SimpleItem.SimpleItem):
    implements(IProxyer)
    __parent__ = None

    def __init__(self, request, cur_url, proxy_folder_addr):
        self.request = request
        self.cur_url = cur_url
        self.proxy_folder_addr = proxy_folder_addr
    
    # TODO: Cache this function
    def get_url( self ):
        cur_url = '/'.join( self.cur_url )
        print 'Fetching "%s"' % cur_url
        
        # User agent should be configurable? Or passed through from the client
        req = urllib2.Request( cur_url, headers = { 'User-Agent': 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11' } )
        con = urllib2.urlopen( req )
        
        info = con.info()
        
        # Get the url in case it has been redirected
        cur_url = con.geturl()
        
        # Make sure the content-type is passed on
        self.request.response.setHeader( 'Content-Type', info['Content-Type'] )
        
        if info.gettype() == 'text/html':
            # Rewrite any URLs (in src & href attribs)
            q = pq( con.read() )
            
            def rewrite_url( url ):
                p = urlparse.urlsplit( url )
                
                # Convert relative urls to absolute
                if p.scheme == '' and p.netloc == '': # Relative URL
                    url = urlparse.urljoin( cur_url, url )
                
                if url.startswith( self.cur_url[0] ): # Absolute URL within the site
                    url = self.proxy_folder_addr + url[len(self.cur_url[0]):]
                
                return url
            
            for el in q( '*[href]' ):
                q(el).attr( 'href', rewrite_url( q(el).attr( 'href' ) ) )

            for el in q( '*[src]' ):
                q(el).attr( 'src', rewrite_url( q(el).attr( 'src' ) ) )
            
            # Grab specific content and place within normal plone page (optional?)
            
            return unicode( q )
        else:
            return con.read()
    
    def __call__( self ):
        return self.get_url()
