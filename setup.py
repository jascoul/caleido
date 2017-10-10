import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()


setup(name='caleido',
      version=0.1,
      description='Caleido',
      long_description=README,
      classifiers=[
          "Programming Language :: Python",
          "Framework :: Pylons",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
          "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)"
      ],
      keywords="web services",
      author='Jasper Op de Coul',
      author_email='jasper.opdecoul@eur.nl',
      url='https://caleido.io',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=['cornice',
                        'cornice_swagger',
                        'pyramid_chameleon',
                        'passlib',
                        'waitress',
                        'sqlalchemy',
                        'sqlalchemy-utils',
                        'pyramid_tm',
                        'pyramid_retry',
                        'pyramid_jwt',
                        'zope.sqlalchemy',
                        'psycopg2',
                        'intervals'],
      entry_points="""\
      [paste.app_factory]
      main=caleido:main
      [console_scripts]
      initialize_db = caleido.tools:initialize_db
      drop_db = caleido.tools:drop_db
      """,
      paster_plugins=['pyramid'])
