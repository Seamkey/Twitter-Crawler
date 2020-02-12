import tweepy

consumer_key = "4vT6TFI7yIdtNsypX17Z163th"
consumer_secret = "v9OgxdEy25mELUU9JOU1k8FsfGtHQOBEDlx3V51oauOzzsqZxz"
access_token = "1227215889461846017-KBoPxWlnrJZ3SZoC9VmedcOG5laF68"
access_token_secret = "bOm10DTuJ2JytBKI1911tVpMCzNMH8pJSDLKcGPl2ZYHQ"

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
#end setup --------------------------------------------------------------

name = 'toni_infante'

public_tweets = api.user_timeline(id = name, count = 5)

for tweet in public_tweets:
    print (tweet.text)
    print (tweet.created_at)
    print()