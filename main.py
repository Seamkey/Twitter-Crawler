import sys
import tweepy

consumer_key = "4vT6TFI7yIdtNsypX17Z163th"
consumer_secret = "v9OgxdEy25mELUU9JOU1k8FsfGtHQOBEDlx3V51oauOzzsqZxz"
access_token = "1227215889461846017-KBoPxWlnrJZ3SZoC9VmedcOG5laF68"
access_token_secret = "bOm10DTuJ2JytBKI1911tVpMCzNMH8pJSDLKcGPl2ZYHQ"

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
#end setup --------------------------------------------------------------

# overwriting tweepy StreamListener class
class Listener(tweepy.StreamListener):

    def __init__(self, output_file = sys.stdout):
        super(Listener, self).__init__()
        self.output_file = output_file

    def on_status(self, status):
        print(status.user.screen_name, status.user.followers_count, file = self.output_file)
        print()

    def on_error(self, status_code):
        print(status_code)
        return False

listener = Listener()
stream = tweepy.Stream(auth = api.auth, listener = listener)

WORDS = ['Corona', 'Racism']
LOCATIONS = [-124.7771694, 24.520833, -66.947028, 49.384472, # Contiguous US
-164.639405, 58.806859, -144.152365, 71.76871, # Alaska
-160.161542, 18.776344, -154.641396, 22.878623] # Hawaii

try:
    print('Starting Stream')
    #stream.sample(languages=['en'])
    stream.filter(track = WORDS, locations = LOCATIONS, languages=['en'])
    
except KeyboardInterrupt as e:
    print('Stream stopped')
finally:
    print('Done')
    stream.disconnect()
    