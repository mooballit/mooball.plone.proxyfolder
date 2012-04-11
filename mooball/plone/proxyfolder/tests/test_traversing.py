# Copyright (c) 2012 Mooball IT
# See also LICENSE.txt
from mooball.plone.proxyfolder import IProxyFolder, IProxyObject
from mooball.plone.proxyfolder.testing import PROXYFOLDER_FUNCTIONAL_TESTING
from mooball.plone.proxyfolder.types.proxyfolder import Proxyer
from plone.app.testing import TEST_USER_ID
from plone.app.testing import setRoles
import os.path
import unittest
import z3c.traverser.interfaces
import zope.publisher.interfaces


class TestProxyFolderTraverser(unittest.TestCase):

    layer = PROXYFOLDER_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']

    def test_subscribers(self):
        traverser = zope.component.getMultiAdapter(
            (Proxyer('foo', u'html'), self.request),
            z3c.traverser.interfaces.ITraverserPlugin)
        self.assertTrue(traverser)

    def test_notfound(self):
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Manager'])
        self.portal.invokeFactory('mooball.plone.proxyfolder', 'pf',
                                  title='Folder')
        traverser = zope.component.getMultiAdapter(
            (self.portal['pf'], self.request),
            z3c.traverser.interfaces.ITraverserPlugin)
        self.assertRaises(zope.publisher.interfaces.NotFound,
                          traverser.publishTraverse,
                          self.request, 'foo')

    def test_traversebase(self):
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Manager'])
        base_url = os.path.join(os.path.dirname(__file__), 'testdata',
                                'traversebase.html')
        self.portal.invokeFactory('mooball.plone.proxyfolder', 'pf',
                                  title='Folder', base_url='file://' + base_url)
        traverser = zope.component.getMultiAdapter(
            (self.portal['pf'], self.request),
            z3c.traverser.interfaces.ITraverserPlugin)
        obj = traverser.publishTraverse(self.request, 'foo')
        self.assertTrue(IProxyObject.providedBy(obj))
        self.assertFalse(IProxyFolder.providedBy(obj))
