.. Python YQL documentation master file, created by
   sphinx-quickstart on Mon Nov 16 08:38:41 2009.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

==========
Python YQL 
==========

Python YQL is a client library for making queries with `Yahoo Query Language <http://developer.yahoo.com/yql/>`_.

    The Yahoo! Query Language is an expressive SQL-like language that lets you query, filter, and join data across Web services. With YQL, apps run faster with fewer lines of code and a smaller network footprint.

    -- `YDN <http://developer.yahoo.com/yql/>`_

Python YQL is written and maintained by `Stuart Colville <http://muffinresearch.co.uk>`_, along with contributions from the community.

QuickStart
----------

.. sourcecode:: sh

    sudo pip install yql

Or alternatively:

.. sourcecode:: sh

    sudo easy_install yql

The following example shows a simple query using the public endpoint. (The API KEY for flickr has been redacted)

.. sourcecode:: python

    >>> import yql
    >>> y = yql.Public()
    >>> query = 'select * from flickr.photos.search where text="panda" and api_key="INSERT_API_KEY_HERE" limit 3';
    >>> result = y.execute(query)
    >>> result.rows
    [{u'isfamily': u'0', u'title': u'Panda can has fruit', u'farm': u'3', u'ispublic': u'1', u'server': u'2605', u'isfriend': u'0', u'secret': u'62ccb5d94e', u'owner': u'99045337@N00', u'id': u'4135649462'}, {u'isfamily': u'0', u'title': u'Hey Panda', u'farm': u'3', u'ispublic': u'1', u'server': u'2799', u'isfriend': u'0', u'secret': u'1632cb8ab8', u'owner': u'99045337@N00', u'id': u'4134889385'}, {u'isfamily': u'0', u'title': u'Panda Lin Hui', u'farm': u'3', u'ispublic': u'1', u'server': u'2737', u'isfriend': u'0', u'secret': u'099b30a0a4', u'owner': u'37843112@N07', u'id': u'4135631774'}]
    >>> for row in result.rows:
    ...     print row.get('title')
    ... 
    Panda can has fruit
    Hey Panda
    Panda Lin Hui

.. note:: 
    To make a query to Flickr you need to get an API key here: http://www.flickr.com/services/apps/create/apply/.


Contents
--------

.. toctree::
    :maxdepth: 3 

    installation
    usage
    contribution
    code
    license
    authors
    changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

