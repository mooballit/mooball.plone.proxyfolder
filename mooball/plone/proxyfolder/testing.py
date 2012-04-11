from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from plone.app.testing.layers import FunctionalTesting
from plone.app.testing.layers import IntegrationTesting
from zope.configuration import xmlconfig
import mooball.plone.proxyfolder


class ProxyFolderBase(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # load ZCML
        xmlconfig.file('configure.zcml', mooball.plone.proxyfolder,
                       context=configurationContext)

    def setUpPloneSite(self, portal):
        # install into the Plone site
        applyProfile(portal, 'mooball.plone.proxyfolder:default')


PROXYFOLDER_FIXTURE = ProxyFolderBase()
PROXYFOLDER_INTEGRATION_TESTING = IntegrationTesting(
    bases=(PROXYFOLDER_FIXTURE,), name="ProxyFolderBase:Integration")
PROXYFOLDER_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PROXYFOLDER_FIXTURE,), name="ProxyFolderBase:Functional")
