# Written by: Wren J. Rudolph

import yql
from yql.storage import FileTokenStore

import os


with open('private.txt', 'r') as auth_file:
    data = auth_file.read().split("\n")

consumer_key = data[0]
consumer_secret = data[1]


y3 = yql.ThreeLegged(consumer_key, consumer_secret)
_cache_dir = '/Users/wrenjr/PycharmProjects/yahoo-fantasy-football-metrics/oauth_token'
if not os.access(_cache_dir, os.R_OK):
    os.mkdir(_cache_dir)

token_store = FileTokenStore(_cache_dir, secret='sasfasdfdasfdaf')

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


query = "select * from fantasysports.games where game_key='nfl'"

data_yql = y3.execute(query, token=token)
data = data_yql.rows

print data
