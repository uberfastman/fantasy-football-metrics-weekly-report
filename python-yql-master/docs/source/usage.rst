=====
Usage
=====

.. currentmodule:: yql

There are three different ways to use YQL. The public endpoint can be used to query public tables. Oauth is used to provide access to the private endpoint which uses both two-legged and three-legged oauth.

First let's take a look at how we can access the data returned from a query. After that we'll look at differences between the Public and Private endpoints.


Accessing the data returned from a query
========================================

Here's a basic query

.. sourcecode:: python

    >>> import yql
    >>> y = yql.Public()
    >>> res = y.execute("use 'http://yqlblog.net/samples/search.imageweb.xml' as searchimageweb; select title from searchimageweb where query='pizza' limit 3")

When the query is successful a YQL object is returned. (New in 0.3)

The YQL object provides a simple interface for getting at the data. To illustrate let's look at an example:

.. sourcecode:: python

    >>> print res
    <yql.YQLObj object at 0xb77adc2c>
    >>> res.rows
    [{u'title': u'<b>Pizza</b> Hut'}, {u'title': u"Domino's <b>Pizza</b> -
    Official Site"}, {u'title': u"Papa John's"}]
    >>> res.rows[0]
    {u'title': u'<b>Pizza</b> Hut'}
    >>> res.rows[1]
    {u'title': u"Domino's <b>Pizza</b> - Official Site"}
    >>> res.query
    u"use 'http://yqlblog.net/samples/search.imageweb.xml' as searchimageweb; select title from searchimageweb where query='pizza' limit 3"
    >>> res.uri
    u'http://query.yahooapis.com/v1/yql?q=use+%27http%3A%2F%2Fyqlblog.net%2Fsamples%2Fsearch.imageweb.xml%27+as+searchimageweb%3B+select+title+from+searchimageweb+where+query%3D%27pizza%27+limit+3'
    >>> res.count
    3

For the most part it will make sense to use the :attr:`YQLObj.rows` property to access your data as this returns a list of the results. This makes looping over the results as easy as:

.. sourcecode:: python

    >>> result = y.execute('select * from flickr.photos.search where text="panda" and api_key=INSERT_API_KEY_HERE" limit 3')
    >>> result.rows
    [{u'isfamily': u'0', u'title': u'Panda can has fruit', u'farm': u'3', u'ispublic': u'1', u'server': u'2605', u'isfriend': u'0', u'secret': u'62ccb5d94e', u'owner': u'99045337@N00', u'id': u'4135649462'}, {u'isfamily': u'0', u'title': u'Hey Panda', u'farm': u'3', u'ispublic': u'1', u'server': u'2799', u'isfriend': u'0', u'secret': u'1632cb8ab8', u'owner': u'99045337@N00', u'id': u'4134889385'}, {u'isfamily': u'0', u'title': u'Panda Lin Hui', u'farm': u'3', u'ispublic': u'1', u'server': u'2737', u'isfriend': u'0', u'secret': u'099b30a0a4', u'owner': u'37843112@N07', u'id': u'4135631774'}]
    >>> for row in result.rows:
    ...     print row.get('title')
    ...
    Panda can has fruit
    Hey Panda
    Panda Lin Hui
    >>>


.. note::


    In version 0.6 this was changed so that if only one row is returned it's still a list so that iterating over the rows is more robust. Prior to version 0.6 results.rows would contain the content of the data.

    The flickr table requires an API KEY which you can get here http://www.flickr.com/services/apps/create/apply/

To access one result when you know you only have one result use the one() method:

.. sourcecode:: python

    >>> result = y.execute('select * from flickr.photos.search where text="panda" and api_key="INSERT_API_KEY_HERE" limit 1')
    >>> result.one()
    {u'isfamily': u'0', u'title': u'Panda can has fruit', u'farm': u'3', u'ispublic': u'1', u'server': u'2605', u'isfriend': u'0', u'secret': u'62ccb5d94e', u'owner': u'99045337@N00', u'id': u'4135649462'}

If there's more than one result NotOneError will be raised:

.. sourcecode:: python

    >>> res = y.execute("select * from upcoming.events where woeid in (select woeid from geo.places where text='North Beach')")
    >>> res.count
    2
    >>> res.one()
    Traceback (most recent call last):
      File "<input>", line 1, in <module>
      File "yql/__init__.py", line 88, in one
        raise NotOneError, "More than one result"
    NotOneError: More than one result

If at any point you want to access the raw data you can use the :attr:`YQLObj.raw` property to access the full dataset as converted from JSON.

Public API Calls
================

The following example shows a simple query using the public endpoint.

.. sourcecode:: python

    >>> import yql
    >>> y = yql.Public()
    >>> query = 'select * from flickr.photos.search where text="panda" limit 3';
    >>> result = y.execute(query)
    >>> print result
    <yql.YQLObj object at 0xb77adc2c>

Private API Calls
=================

Calls can be made to the private YQL API endpoint and use Oauth for authentication. To use authenticated API calls you will need to have signed up for an API key. When you do so be sure to say that you want to be able to make both public and private API calls.

Oauth supports two and three-legged Oauth. Two-legged is used to sign requests and this route can be taken for YQL queries that doen't require access to private data. Using two-legged auth is recommended for general purpose usage of YQL. Three-legged auth is more involved in that it requires the end-user to authorise access to their data. Three-legged auth is used to access contacts and other aspects of Yahoo's Open Social APIs.


Two-legged Auth
---------------

Here's an example of using Two-legged authentication in Python YQL.

.. sourcecode:: python

    import yql

    y = yql.TwoLegged(API_KEY, SHARED_SECRET)
    y.execute("select * from flickr.photos.search where text='panda' and api_key='INSERT_API_KEY_HERE' limit 3")


Three-legged Auth
-----------------

Three-legged auth requires the user to authenticate with a browser. The idea of this implementation is to try and make using YQL with Three-legged Oauth as painless as possible.

Here's an example:


.. sourcecode:: python

    import yql

    y3 = yql.ThreeLegged(API_KEY, SECRET)
    query = 'select * from social.connections where owner_guid=me'

    request_token, auth_url = y3.get_token_and_auth_url()

    # -- USER AUTHENTICATES HERE --

    access_token = y3.get_access_token(request_token, verifier)
    y3.execute(query, token=access_token)


.. currentmodule:: yql.ThreeLegged

In the example above the first call made uses the method :meth:`get_token_and_auth_url`. This returns a tuple containing the request token and an authentication url. It's up to the implentation to then send or prompt the user to visit that authenication url in order to login to Yahoo.

If a callback was specified in the :meth:`get_token_and_auth_url` method then your user will be sent to that url when they login. The url will automatically be sent the "verifier" string to use in the "get_access_token" method.

If no callback was specified or was explicitly marked as 'oob' (the default value) then the user will be shown a verfier code which they will have to provide to your application.

The next call, :meth:`get_access_token` requires the request token and verifier to be sent in order to provide the token that can be used to make authenicated requests.

Once you have got the ``access_token`` it should be used to execute the query.

The Token can be re-used for subsequent requests but after an hour it will expire and will need to be refreshed.

The :meth:`refresh_token` method can be used to request a new token using the expired token.

Using Storage Classes
=====================

:mod:`yql.storage` provides a basic way to store Tokens on the filesystem to make it easier to re-use access_tokens in YQL queries.

Here's an example:

.. sourcecode:: python

    import yql
    from yql.storage import FileTokenStore

    y3 = yql.ThreeLegged(API_KEY, SECRET)

    path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cache'))
    token_store = FileTokenStore(path, secret='gfdlgkfruwopiruowsd')

    query = 'select * from social.connections where owner_guid=me'
    stored_token = token_store.get('foo')

    if not stored_token:
        # Do the dance
        request_token, auth_url = y3.get_token_and_auth_url()
        print "Visit url %s and get a verifier string" % auth_url
        verifier = raw_input("Enter the code: ")
        token = y3.get_access_token(request_token, verifier)
        token_store.set('foo', token)
    else:
        # Check access_token is within 1hour-old and if not refresh it
        # and stash it
        token = y3.check_token(stored_token)
        if token != stored_token:
            token_store.set('foo', token)

    print y3.execute(query, token=token)


This example shows a way to do the initial dance including authentication. The access token provided is then stashed away in a file for re-use on subsequent calls. When re-used the :meth:`check_token` method is used to check if the token needs refreshing. If it's over an hour old the token is refreshed and returned.

The Storage classes are designed to be extended as necessary so that the user can implement a different backend for storing tokens for re-use. An example would be to use memcache for storage. To create a new storage class all that's needed is to subclass :class:`yql.storage.BaseTokenStorage`.

.. note::

    It's worth bearing in mind that :class:`yql.storage.FileTokenStorage` at this point in time, is not intended for heavy duty production use and it's recommended to create a subclass tailored to your own needs.


Other YQL Features
==================

Here's some details on other YQL features that are supported by Python-yql.

Using data tables with environment files
----------------------------------------

YQL has feature that enables an externally hosted environment file to be used to import open tables for use with your app.

See the YQL documentation here: `YQL opentables environment <http://developer.yahoo.com/yql/guide/yql-opentables-import.html#yql-opentables-import-environment>`_

To use this feature create and host your environment file and then use it like so:

.. sourcecode:: python

    >>> import yql
    >>> y = yql.Public()
    >>> env = "http://datatables.org/alltables.env"
    >>> query = "SHOW tables;"
    >>> y.execute(query, env=env)


Using Placeholders in Queries
-----------------------------

This example uses the optional query placeholders which are strings prefixed with ``@`` which are substitutued by dictionary items whose keys match the placeholder.

.. note::

    Python YQL validates placeholders to check that the correct number of substitutions are passed into the execute function.

.. sourcecode:: python

    >>> import yql
    >>> y = yql.Public()
    >>> query = 'select * from flickr.photos.search where text=@text limit 3';
    >>> y.execute(query, {"text": "panda"})


.. note::
    Issues have been noted using placeholders within SET queries. This needs further investigation but it appears to be a bug outside of the python-yql library.

Using INSERT, UPDATE and DELETE
-------------------------------

As of version (0.4) python-yql supports INSERT, UPDATE and DELETE queries.

Here's an example of an INSERT using the bit.ly table:

.. sourcecode:: python

        query = """USE 'http://yqlblog.net/samples/bitly.shorten.xml';
                   insert into bitly.shorten(login, apiKey, longUrl)
                   values('%s','%s','http://yahoo.com')""" % (
                                            BITLY_USER, BITLY_API_KEY)
        y = yql.Public()
        res = y.execute(query)

Logging for debugging purposes
-------------------------------

As of version 0.5 logging has been made available. It's off by default, however it is possible to control logging and turn it on using environment variables.

* YQL_LOGGING - Set to a value e.g: 1 to turn on logging.
* YQL_LOG_DIR - the directory that logs are written to.
* YQL_LOGGING_LEVEL - Should be one of 'debug', 'info', 'warning', 'error', 'critical'.

For debugging setting the level to "debug" will provide the most insight into what's happening.

Using python-yql in Google App Engine
======================================
As of version 0.7.4 we've deprecated support for Python 2.5. As a result of this change if you're using python-yql under GAE you'll need to use the python 2.7 runtime. See https://developers.google.com/appengine/docs/python/runtime for more information.
