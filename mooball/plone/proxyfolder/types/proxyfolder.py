from plone.directives import form
from zope import schema
from zope.interface import Interface, implements
from five import grok

import zope.component
import zope.publisher.interfaces

import OFS.SimpleItem


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
        else:
            if 'url_builder' not in request:
                request['url_builder'] = Proxyer(self.context.base_url,self.context, request)
            
            request['url_builder'].url.append( name )
            
            return request['url_builder']
            
            raise zope.publisher.interfaces.NotFound(
                self.context, name, self.request)

class IProxyer( Interface ):
    pass

class Proxyer( OFS.SimpleItem.SimpleItem ):
    implements( IProxyer )
    
    def __init__( self, base_url, context, request ):
        self.url = [ base_url ]
        self.context = context
        self.request = request
    
    def join_url( self ):
        return '/'.join( self.url )
    
    def __call__( self ):
        return self.joinurl()
