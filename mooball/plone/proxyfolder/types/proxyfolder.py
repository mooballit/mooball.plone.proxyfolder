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
import urllib, urllib2, urlparse
from time import time
from plone.memoize import ram

class IProxyer( Interface ):
    def get_data():
        '''Fetches the data from the provided url'''

class IProxyFolder( form.Schema ):
    title = schema.TextLine( title=u'Title')
    base_url = schema.TextLine( title=u'Base URL')
    proxy_images = schema.Bool( title = u'Proxy Images?', default = False )
    content_selector = schema.TextLine( title=u'Content CSS Selector', required = False, description = u'The CSS Selector will be used to grab a specific part of the remove html and place it within the plone design.' )
    head_data = schema.Text( title=u'Content in Head', required = False )
    user_agent = schema.TextLine( title = u'HTTP User agent', required = False, description = u'The User Agent to pass with the proxy http requests. Leave empty to just pass through the clients User Agent.' )
    url_attrs = schema.TextLine( title = u'Extra URL Attributes', required = False, description = u'Comma separated list of attribute names that contain URLs that needs rewriting (ie. other than the standard src and href)' )
    
class ProxyFolder( Item ):
    implements( IProxyer )
    
    def get_data( self ):
        proxy = Proxyer( self, self.REQUEST, [ self.base_url ], self )
        proxy.__parent__ = self
        return proxy.__of__(self).get_data()
        

class ProxyTraverser(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        
    def publishTraverse(self, request, name):
        print name
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
            self.request['proxy_folder'] = self.context

        self.request['cur_remote_path'].append( name )
        
        proxy = Proxyer( self.context, self.request, self.request['cur_remote_path'],self.request['proxy_folder'] )
        proxy.__parent__ = self.context
        return proxy.__of__(self.context)

def _get_data_cachekey( method, self ):
    # Will cache a specific page for a day.
    return ( self.cur_url, time() // ( 60 * 60 * 24 ), self.proxy_folder.base_url, self.proxy_folder.proxy_images, self.proxy_folder.content_selector, self.proxy_folder.url_attrs )


class Proxyer(OFS.SimpleItem.SimpleItem):
    implements(IProxyer)
    __parent__ = None

    def __init__(self, context, request, cur_url, proxy_folder):
        self.context = context
        self.request = request
        self.cur_url = cur_url
        self.id = cur_url[-1]
        self.proxy_folder = proxy_folder
        self.proxy_folder_addr = self.proxy_folder.absolute_url()
    
    @ram.cache( _get_data_cachekey )
    def get_data( self ):
        # Build the url
        cur_url = '/'.join( [ self.cur_url[0] ] + [ urllib.quote( p ) for p in self.cur_url[1:] ] )
        print 'Fetching "%s"' % cur_url
        
        # User agent should be configurable? Or passed through from the client
        req = urllib2.Request( cur_url, headers = { 'User-Agent': self.request['HTTP_USER_AGENT'] } )
        con = urllib2.urlopen( req )
        
        info = con.info()
        
        # Get the url in case it has been redirected
        cur_url = con.geturl()
        
        # Make sure the content-type is passed on
        self.request.response.setHeader( 'Content-Type', info['Content-Type'] )
        
        if info.gettype() == 'text/html':
            q = pq( con.read() )
            
            # Rewrite any URLs (in src & href attribs + user specified ones)
            def rewrite_url( url, normalize_only = False ):
                p = urlparse.urlsplit( url )
                
                # Convert relative urls to absolute
                if p.scheme == '' and p.netloc == '': # Relative URL
                    url = urlparse.urljoin( cur_url, url )
                
                if not normalize_only and url.startswith( self.cur_url[0] ): # Absolute URL within the site
                    url = self.proxy_folder_addr + url[len(self.cur_url[0]):]
                
                return url
            
            url_attrs = ['href','src']
            
            if self.proxy_folder.url_attrs:
                url_attrs += [ a.strip() for a in str( self.proxy_folder.url_attrs ).split(',') ]
            
            for attr in url_attrs:
                for el in q( '*[%s]' % attr ):
                    q(el).attr( attr, rewrite_url( q(el).attr( attr ), el.tag == 'img' and not self.proxy_folder.proxy_images ) )
            
            # Grab specific content and place within normal plone page
            if self.proxy_folder.content_selector:
                q = q( str( self.proxy_folder.content_selector ) )
            
            return unicode( q ).replace( u'&#13;', u'\n' )
        else:
            return con.read()

class View( grok.View ):
    grok.context( IProxyer )
    grok.name( 'index_html' )
