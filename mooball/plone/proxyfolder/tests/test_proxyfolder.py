# Copyright (c) 2012 Mooball IT
# See also LICENSE.txt
from mooball.plone.proxyfolder.testing import PROXYFOLDER_FUNCTIONAL_TESTING
from mooball.plone.proxyfolder.types.proxyfolder import IProxyFolder
from plone.dexterity.factory import DexterityFactory
import unittest
import zope.interface


class TestProxyFolder(unittest.TestCase):

    layer = PROXYFOLDER_FUNCTIONAL_TESTING

    def test_pass(self):
        factory = DexterityFactory(
            portal_type='mooball.plone.proxyfolder.types.proxyfolder')
        self.assertTrue(
            zope.interface.verify.verifyObject(
                IProxyFolder, factory()))
