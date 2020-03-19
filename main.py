import sys
import tweepy
import pymongo
import json
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import pandas as pd
import itertools

consumer_key = "4vT6TFI7yIdtNsypX17Z163th"
consumer_secret = "v9OgxdEy25mELUU9JOU1k8FsfGtHQOBEDlx3V51oauOzzsqZxz"
access_token = "1227215889461846017-KBoPxWlnrJZ3SZoC9VmedcOG5laF68"
access_token_secret = "bOm10DTuJ2JytBKI1911tVpMCzNMH8pJSDLKcGPl2ZYHQ"

client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["Twitter-Data"]
col = db["Tweets"]
#end setup --------------------------------------------------------------

# overwriting tweepy StreamListener class
class Listener(tweepy.StreamListener):

    def __init__(self, output_file = sys.stdout):
        super(Listener, self).__init__()
        self.output_file = output_file

    def on_status(self, status):
        print(status.user.screen_name, '\n', status.text, file = self.output_file)
        col.insert_one(json.loads(status))
        print()
        print()

    def on_data(self, data):
        col.insert_one(json.loads(data))

    def on_error(self, status_code):
        print(status_code)
        return False

def streamData():
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit_notify=True, wait_on_rate_limit=True)

    listener = Listener()
    stream = tweepy.Stream(auth = api.auth, listener = listener, tweet_mode = "extended")

    uk_trends = api.trends_place(12723)
    WORDS = ['a', 'all', 'is', 'was', 'the', 'on', 'COVID-19', 'Corona', 'Bernie', 'Biden']
    for trend in uk_trends[0]["trends"]:
        WORDS.append(trend["name"])
    print(WORDS)

    try:
        print('Starting Stream')
        for i in range(8):
            stream.filter(track = WORDS, languages=['en'], is_async=True)
            time.sleep(900)
            print("%d minutes passed" %((i+1)*15))
            stream.disconnect()
    except KeyboardInterrupt as e:
        print('Stream stopped')
    finally:
        print('Done')
        stream.disconnect()

def RESTprobeData():
    #TODO
    return

def clusterData(skipval = 0, limitval = 100):
    fetchResult = col.find({}, {"text":1}).skip(skipval).limit(limitval)
    tweets = []
    ids = []
    #filter tweets without text
    for tweet in fetchResult:
        try:
            tweets.append(tweet["text"])
            ids.append(tweet["_id"])
        except KeyError:
            pass
    
    #cluster data
    vectorizer = TfidfVectorizer(stop_words='english')
    k = int((len(tweets) * 0.1))
    model = KMeans(n_clusters=k, max_iter=500)
    model.fit(vectorizer.fit_transform(tweets))

    groups = pd.DataFrame({"group": model.labels_, "tweetID": ids}).groupby(["group"])
    return [group["tweetID"].tolist() for item, group in groups]

def generateClusterStats(idClusters):
    clusters = []
    for cluster in idClusters:
        clusters.append(
            [col.find_one({"_id": ID}, {"_id": 0, "user": 1, "entities": 1}) for ID in cluster]
        )

    allHashtags = []
    allUsers = []

    for cluster in clusters:            
        hashtags = []
        mentions = []

        for hashtaglist in [tweet["entities"]["hashtags"] for tweet in cluster if tweet["entities"]["hashtags"]]:
            hashtags = [hashtag["text"] for hashtag in hashtaglist]
        
        for mentionlist in [tweet["entities"]["user_mentions"] for tweet in cluster if tweet["entities"]["user_mentions"]]:
            mentions = [mention["screen_name"] for mention in mentionlist]
        
        users = [tweet["user"] for tweet in cluster]
        print(getImportantUsers(users))
        allUsers.append(users)
        # print("hashtags: ", hashtags)
        # print("mentions: ", mentions)
        allHashtags.append(hashtags)

    # print(flatten(allHashtags))

def flatten(listOfLists):
    return list(itertools.chain(*listOfLists))

def getImportantUsers(users):
    #find user with highest number of followers
    importantUsers = {"following": 0, "statuses": 0}
    importantUsers["following"] = max([[user["followers_count"], user["screen_name"]] for user in users])[1]
    importantUsers["statuses"] = max([[user["statuses_count"], user["screen_name"]] for user in users])[1]
    return importantUsers


# streamData()
clusters = clusterData(limitval=500)
generateClusterStats(clusters)