
Caleido, a Research Intelligence platform
=========================================

.. image:: https://travis-ci.org/jascoul/caleido.svg?branch=master
    :target: https://travis-ci.org/jascoul/caleido

This is a work-in-progress, research project from Erasmus University Library Rotterdam.

Installation
------------

Caleido is being developed as a python3 app, with a dependency on PostgreSQL 9.5
To install the software:

```bash
> git clone https://github.com/jascoul/caleido.git
> cd caleido
> virtualenv --python=python3 .
> source bin/activate
> pip install -e .
```

Next, create a PostgreSQL database with the same user/password as the caleido.ini file
(Have a look at the psql commands in the travis.yaml file)

To generate the initial database, run the initialize_db script from the bin folder

```bash
> initialize_db caleido.ini
```

To run the unittests, install tox, and run the tox command

```bash
> pip install tox
> tox
```

Or, start a webserver and visit the API at http://localhost:6543/api/swagger.html

```bash
> pserve caleido.ini
```
