from five import grok
from plone.dexterity.content import Item
from plone.directives import form
from zope import schema
from zope.interface import Interface, implements
import OFS.SimpleItem
import z3c.traverser.interfaces
import zope.component
import zope.publisher.interfaces


class IProxyFolder(form.Schema):
    title = schema.TextLine(title=u'Title')
    base_url = schema.TextLine(title=u'Base URL')


class IProxyObject(Interface):
    """ A proxy object representig a URL fragment to the remote site.
    """


class ProxyFolder(Item):
    grok.implements(IProxyObject)

    def acquireProxyFolder(self):
        return self


class ProxyTraverser(grok.MultiAdapter):
    grok.provides(z3c.traverser.interfaces.ITraverserPlugin)
    grok.adapts(IProxyObject,
                zope.publisher.interfaces.IPublisherRequest)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        view = zope.component.queryMultiAdapter(
            (self.context, self.request), name=name)
        if view is not None:
            return view
        pf = self.context.acquireProxyFolder()
        base_url = pf.base_url
        if not base_url:
            raise zope.publisher.interfaces.NotFound(
                self.context, name, self.request)


class Proxyer(OFS.SimpleItem.SimpleItem):
    implements(IProxyObject)
