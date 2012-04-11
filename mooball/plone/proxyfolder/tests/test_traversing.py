# Copyright (c) 2012 Mooball IT
# See also LICENSE.txt
from mooball.plone.proxyfolder.testing import PROXYFOLDER_FUNCTIONAL_TESTING
from mooball.plone.proxyfolder.types.proxyfolder import Proxyer
import z3c.traverser.interfaces
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
import unittest
import zope.publisher.interfaces


class TestProxyFolderTraverser(unittest.TestCase):

    layer = PROXYFOLDER_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']

    def test_subscribers(self):
        traverser = zope.component.getMultiAdapter(
            (Proxyer(), self.request),
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
