# Copyright (c) 2012 Mooball IT
# See also LICENSE.txt
from mooball.plone.proxyfolder.testing import PROXYFOLDER_FUNCTIONAL_TESTING
import unittest


class TestProxyFolder(unittest.TestCase):

    layer = PROXYFOLDER_FUNCTIONAL_TESTING

    def test_pass(self):
        self.assertTrue(1)
