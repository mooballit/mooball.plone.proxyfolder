from setuptools import setup, find_packages
import os

version = '0.3.1'
tests_require = ['plone.app.testing',
                ]

setup(name='mooball.plone.proxyfolder',
      version=version,
      description="",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        ],
      keywords='',
      author='Martin Hulten-Ashauer',
      author_email='martin@mooball.com',
      url='http://svn.plone.org/svn/collective/',
      license='ZPL 2.1',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['mooball', 'mooball.plone'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'Products.CMFPlone',
          'plone.app.dexterity',
          'z3c.traverser',
          'pyquery',
      ],
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone
      """,
      extras_require=dict(tests=tests_require),
      )
