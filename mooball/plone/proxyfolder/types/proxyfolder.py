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
import urllib, urllib2, urlparse, re, Cookie
from time import time
from plone.memoize import ram
from z3c.form import field
from plone.namedfile.utils import set_headers, stream_data

class IProxyTraversable( Interface ):
    pass

class IProxyHTML( Interface ):
    def get_data():
        pass
class IProxyData( Interface ):
    def get_data():
        pass

class IProxyFolder( form.Schema ):
    title = schema.TextLine( title=u'Title')
    base_url = schema.TextLine( title=u'Base URL')
    proxy_images = schema.Bool( title = u'Proxy Images?', default = False )
    content_selector = schema.TextLine( title=u'Content CSS Selector', required = False,
        description = u'The CSS Selector will be used to grab a specific part of the remove html and place it within the plone design.' )
    head_data = schema.Text( title=u'Content in Head', required = False )
    user_agent = schema.TextLine( title = u'HTTP User agent', required = False,
        description = u'The User Agent to pass with the proxy http requests. Leave empty to just pass through the clients User Agent.' )
    url_attrs = schema.TextLine( title = u'Extra URL Attributes', required = False,
        description = u'Comma separated list of attribute names that contain URLs that needs rewriting (ie. other than the standard src and href)' )
    exclude_urls = schema.Text( title = u'Non-template URLs', required = False,
        description = u'Each line is a regular expression that when matched against a URL will supress the plone header and footer from being applied to it\'s data. The Content CSS Selector will not be applied either. Any links, however, will be rewriten as usual.')
    exclude_ajax = schema.Bool( title = u'Dont apply template to AJAX requests?', default = True,
        description = u'This will make sure any AJAX request do not get the Plone Template applied to them. If this does not work, please use the above field to match URLs instead.')
    nocache_urls = schema.Text( title = u'Do not cache these URLs', required = False,
        description = u'Each line is a regular expression that when matched against a URL will prevent it from being cached')
    nocache_cookies = schema.Text( title = u'Do not cache pages when these cookies are set', required = False,
        description = u'Each line is the key name of a cookie which, when set, will prevent anything from being cached.')

class EditForm( form.SchemaEditForm ):
    grok.name( 'edit' )
    grok.context( IProxyFolder )
    
    schema = IProxyFolder
    
    fields = field.Fields(IProxyFolder)
    
    def update( self ):
        # TODO: Add code to remove trailing slashes from base_url field
        #       Remove similar functionality from elsewhere in this code.
        
        # Check if the clear_cache checkbox was ticked
        if 'form.widgets.clear_cache' in self.request.form:
            if self.request.form.pop( 'form.widgets.clear_cache' ): #pop-n-check!
                # Invalidate the cache for the get_data function.
                ram.choose_cache( 'mooball.plone.proxyfolder.types.proxyfolder.get_data' ).ramcache.invalidate( 'mooball.plone.proxyfolder.types.proxyfolder.get_data' )
        
        super( EditForm, self ).update()
    
    def updateWidgets( self ):
        self.fields += field.Fields(
            schema.Bool(
                __name__ = 'clear_cache',
                title = u'Clear the cache',
                required = False
            
             )
        )
        super( EditForm, self ).updateWidgets()
        self.widgets['head_data'].style = u"height: 300px;"
        self.widgets['exclude_urls'].style = u"height: 150px; width: 600px;"
        
    

class ProxyFolder( Item ):
    implements( IProxyTraversable, IProxyHTML )
    
    def get_data( self ):
        return get_data( [ self.base_url ], self, self.REQUEST ).get_data()
        

class DummyItem( grok.Model ):
    implements( IProxyTraversable )
    
    def __init__( self, cur_url, proxy_folder ):
        self.cur_url = cur_url
        self.proxy_folder = proxy_folder


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

        if isinstance( self.context, ProxyFolder ):
            cur_url = [ self.context.base_url ]
            proxy_folder = self.context
        else:
            cur_url = self.context.cur_url
            proxy_folder = self.context.proxy_folder
        
        cur_url.append( name )

        if self.request.path == []: # Traverser at end of url
            ret = get_data( cur_url, proxy_folder, self.request )
            # Because the get_data function is cached sometimes, the returned object's REQUEST attr might not be correct (missing stuff).
            # So therefore we just set it to the correct one
            ret.REQUEST = self.request
            return ret
        else:
            if isinstance( self.context, ProxyFolder ):
                return DummyItem( cur_url, self.context )
            else:
                return self.context

class View( grok.View ):
    grok.context( IProxyHTML )
    grok.name( 'index' )

class DataView( grok.View ):
    grok.context( IProxyData )
    grok.name( 'index' )
    
    def render( self ):
        self.request.response.setHeader( 'Content-Type', self.context.content_type )
        return self.context.get_data()


class ProxyHTML( grok.Model ):
    implements( IProxyHTML )
    
    __parent__ = None
    _id = None
    
    content_type = 'text/html'
    
    def __init__( self, data ):
        self.data = data
    
    def get_data( self ):
        return self.data

class ProxyData( grok.Model ):
    implements( IProxyData )
    
    __parent__ = None
    _id = None
    
    def __init__( self, data, content_type ):
        self.content_type = content_type
        self.data = data
    
    def get_data( self ):
        return self.data

def _get_data_cachekey( method, url, proxy_folder, request ):
    # Will cache a specific page ( plus any data sent to page via POST/GET ) for a day.
    # Also supports change-of-settings invalidation
    
    # Check if specific cookies are set thus disabling caching.
    if proxy_folder.nocache_cookies:
        for nc_cookie in proxy_folder.nocache_cookies.split( '\n' ):
            if nc_cookie.strip() in request.cookies:
                print 'nocache! cause of cookieeee'
                raise ram.DontCache
                
    # Check if the url is to be excluded from cache
    if proxy_folder.nocache_urls:
        for nc_url in proxy_folder.nocache_urls.split( '\n' ):
            if re.match( nc_url.strip(), '/'.join( url ) ):
                print 'nocache!'
                raise ram.DontCache
    
    return ( url, request.form, time() // ( 60 * 60 * 24 ), proxy_folder.base_url, proxy_folder.proxy_images, proxy_folder.content_selector, proxy_folder.url_attrs, proxy_folder.exclude_urls )

@ram.cache( _get_data_cachekey )
def get_data( url, proxy_folder, request ):
    proxy_folder_addr = proxy_folder.absolute_url()

    # Build the url
    req_url = '/'.join( [ url[0] ] + [ urllib.quote( p ) for p in url[1:] ] )
    
    print 'Fetching %s ...' % req_url,

    if request['QUERY_STRING'] != '':
        # Querying http://www.domain.com?query_string will give an error
        # This fixes it.
        if req_url == proxy_folder.base_url and not req_url.endswith( '/' ):
            req_url += '/'
        
        p = urlparse.urlparse( req_url )
        req_url = urlparse.urlunparse( p[:4] + ( request['QUERY_STRING'], ) + p[5:] )
    
    req = urllib2.Request( req_url, headers = { 'User-Agent': proxy_folder.user_agent or request['HTTP_USER_AGENT'],
                                                'X-Requested-With': request['HTTP_X_REQUESTED_WITH'],
                                                'Cookie': request['HTTP_COOKIE'] } )

    post_data = request.form
    
    if post_data:
        # Pass on any POST data.
        
        # Because there is no specific source for only POST data in Zope
        # we need to use data from request['form'] and then remove
        # anything that has the same keys as what is in the QUERY_STRING
        if request['QUERY_STRING'] != '':
            for key in urlparse.parse_qs( request['QUERY_STRING'] ):
                if key in post_data:
                    del post_data[ key ]
        
        if post_data:
            req.add_data( urllib.urlencode( post_data ) )

    # Prevents redirects from being handled.
    class RedirectPreventer( urllib2.HTTPRedirectHandler ):
        def http_error_302( self, req, fp, code, msg, headers ):
            pass
        
        http_error_301 = http_error_303 = http_error_307 = http_error_302

    opener = urllib2.build_opener( RedirectPreventer )
    urllib2.install_opener( opener )

    try:
        con = urllib2.urlopen( req )
    except urllib2.HTTPError, e:
        # If it is a redirect error rewrite the location and pass the redirect on
        if e.code in [ 301, 302, 303, 307 ]:
            # Pass on any cookies
            if e.hdrs.get( 'set-cookie' ):
                cookies = Cookie.BaseCookie( e.hdrs.get( 'set-cookie' ) )
                
                for cookie in cookies.values():
                    request.response.appendHeader( 'set-cookie', cookie.OutputString() )
                
            # Rewrite the location
            location = e.hdrs['location']
            location = '/'.join( list( proxy_folder.getPhysicalPath() ) + location.split( '/' )[1:] )
            
            request.response.redirect( location, status = e.code )
            
            ret = ProxyData( '', 'text/plain' )
            ret.__parent__ = proxy_folder
            ret._id = url[-1]
            return ret

        raise

    
    print 'DONE'
    
    info = con.info()
    
    # Get the url in case it has been redirected
    req_url = con.geturl()
    
    # Make sure the content-type is passed on
    request.response.setHeader( 'Content-Type', info[ 'Content-Type' ] )
    
    # Make sure cookies are passed on as well.
    if info.get( 'set-cookie' ):
        request.response.appendHeader( 'Set-Cookie', info.get( 'set-cookie' ) )
    
    if info.gettype() == 'text/html':
        q = pq( con.read() )
        
        # Rewrite any URLs (in src & href attribs + user specified ones)
        def rewrite_url( attr_url, normalize_only = False ):
            if attr_url.startswith( '#' ):
                return attr_url
                
            p = urlparse.urlsplit( attr_url )
            
            # Convert relative urls to absolute
            if p.scheme == '' and p.netloc == '':
                attr_url = urlparse.urljoin( req_url, attr_url )
            
            # Rewrite the absolute urls (if they are from the remote site)
            if not normalize_only and attr_url.startswith( url[0] ):
                attr_url = proxy_folder_addr + attr_url[ len( url[0] ): ]
            
            return attr_url
        
        # Find any URL attributes and rewrite them
        url_attrs = ['href','src','action']
        if proxy_folder.url_attrs:
            url_attrs += [ a.strip() for a in str( proxy_folder.url_attrs ).split(',') ]
        
        for attr in url_attrs:
            for el in q( '*[%s]' % attr ):
                q(el).attr( attr, rewrite_url( q(el).attr( attr ), el.tag == 'img' and not proxy_folder.proxy_images ) )
        
        # Check if it is an ajax query and if it should not use the template
        if proxy_folder.exclude_ajax and request['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
            ret = ProxyData( unicode( q ).replace( u'&#13;', u'\n' ), info['Content-Type'] )
            ret.__parent__ = proxy_folder
            ret._id = url[-1]
            return ret
        
        # Check if the url is to be excluded from the template
        if proxy_folder.exclude_urls:
            exclude_urls = [ re.compile( line.strip() ) for line in proxy_folder.exclude_urls.split( '\n' ) ]
            for eu in exclude_urls:
                if eu.match( req_url ):
                    ret = ProxyData( unicode( q ).replace( u'&#13;', u'\n' ), info['Content-Type'] )
                    ret.__parent__ = proxy_folder
                    ret._id = url[-1]
                    return ret


        # Grab specific content and place within normal plone page
        if proxy_folder.content_selector:
            q = q( str( proxy_folder.content_selector ) )
        
        
        ret = ProxyHTML( unicode( q ).replace( u'&#13;', u'\n' ) )
        ret.__parent__ = proxy_folder
        ret._id = url[-1]
        
        return ret.__of__( proxy_folder )
    else:
        ret = ProxyData( con.read(), info['Content-Type'] )
        ret.__parent__ = proxy_folder
        ret._id = url[-1]
        return ret
