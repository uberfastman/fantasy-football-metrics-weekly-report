========================================
This project is not actively maintained.
========================================

*Looking back at this project it's not where I would like it to be and I don't have the necessary time to 
update it so it remains here purely for posterity.*


==========
Python YQL
==========

Python YQL is a client library for making queries with Yahoo Query Language.


Test Status
============

.. image:: https://secure.travis-ci.org/project-fondue/python-yql.png
   :target: http://travis-ci.org/project-fondue/python-yql

Installation
============

::

    pip install yql

or 

::

    easy_install yql

Usage
=====

::

    >>> import yql
    >>> y = yql.Public()
    >>> query = 'select * from flickr.photos.search where text=@text and api_key="INSERT_API_KEY_HERE" limit 3';
    >>> y.execute(query, {"text": "panda"})


Source-code
===========

Branches exist at https://github.com/project-fondue/python-yql


Contributions
=============

Bug-fixes/Features/Patches always welcome - please submit a pull request on github.com

