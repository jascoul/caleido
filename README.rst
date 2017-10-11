.. highlight:: rst

Caleido, a Research Intelligence platform
=========================================

.. image:: https://travis-ci.org/jascoul/caleido.svg?branch=master
    :target: https://travis-ci.org/jascoul/caleido

This is a work-in-progress, research project from Erasmus University Library Rotterdam.

Setting up Caleido
------------------

* Install Python3.4 or newer
* Install PostgreSQL 9.5 or newer
* Clone the repository, create a virtualenv, install dependencies::

    git clone https://github.com/jascoul/caleido.git
    cd caleido
    virtualenv --python=python3 .
    source bin/activate
    pip install -e .

* Create a PostgreSQL database with the same user/password as the caleido.ini file (Have a look at the psql commands in the travis.yaml file)
* Initialized the database with the initialize_db script::

    initialize_db caleido.ini

Tests
-----

* Install tox and optionally pytest::

    pip install tox
* Run tox::

    tox 

Running the API
---------------

* Start the development webserver::

    pserve caleido.ini

* Visit the API browser at http://localhost:6543/api/swagger.html

