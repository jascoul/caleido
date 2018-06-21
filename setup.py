import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'requirements.txt')) as f:
    REQUIREMENTS = f.read().splitlines()


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
      install_requires=REQUIREMENTS,
      entry_points="""\
      [paste.app_factory]
      main=caleido:main
      [console_scripts]
      initialize_db = caleido.tools:initialize_db
      drop_db = caleido.tools:drop_db
      bigquery_schema = caleido.tools:bigquery_schema
      """,
      paster_plugins=['pyramid'])
