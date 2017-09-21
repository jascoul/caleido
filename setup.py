import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()


setup(name='scributor',
      version=0.1,
      description='Scributor',
      long_description=README,
      classifiers=[
          "Programming Language :: Python",
          "Framework :: Pylons",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"
      ],
      keywords="web services",
      author='',
      author_email='',
      url='',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=['cornice',
                        'waitress',
                        'sqlalchemy',
                        'sqlalchemy-utils',
                        'pyramid_tm',
                        'pyramid_retry',
                        'zope.sqlalchemy',
                        'psycopg2',
                        'intervals'],
      entry_points="""\
      [paste.app_factory]
      main=scributor:main
      """,
      paster_plugins=['pyramid'])