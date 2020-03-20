import sys
import tweepy
import pymongo
import json
import time

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import pandas as pd

import networkx as nx
import matplotlib.pyplot as plt

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

    #Find words to stream with
    uk_trends = api.trends_place(12723)
    WORDS = ['a', 'all', 'is', 'was', 'the', 'on', 'COVID-19', 'Corona', 'Bernie', 'Biden']
    for trend in uk_trends[0]["trends"]:
        WORDS.append(trend["name"])

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
    model = KMeans(n_clusters=k, max_iter=300)
    model.fit(vectorizer.fit_transform(tweets))
 
    return pd.DataFrame({"group": model.labels_, "tweetID": ids}).groupby(["group"])

clusters = []
def buildClusters(groups):
    idClusters = [group["tweetID"].tolist() for _, group in groups]
    for cluster in idClusters:
        clusters.append(
            [col.find_one({"_id": ID}, {"_id": 0, "user": 1, "entities": 1}) for ID in cluster]
        )
    return

overall_mention_network = {}
overall_hashtag_network = {} #A: [#B, #C]

def generateNetwork():
    for cluster in clusters:  
        mention_network = {}
        hashtag_network = {}          
        for tweet in cluster:
            user = tweet["user"]
            hashtags = tweet["entities"]["hashtags"]
            mentions = tweet["entities"]["user_mentions"]

            if not user["id_str"] in mention_network:
                mention_network[user["id_str"]] = []
            for mention in mentions:
                if not mention["id_str"] in mention_network:
                    mention_network[mention["id_str"]] = []
                if mention["id_str"] not in mention_network[user["id_str"]]:
                    mention_network[user["id_str"]].append(mention["id_str"])

            for hashtag in hashtags:
                if not hashtag["text"] in hashtag_network:
                    hashtag_network[hashtag["text"]] = []
                intermediate = [x["text"] for x in hashtags if x["text"] != hashtag["text"]] #hashtag list without the current hashtag
                hashtag_network[hashtag["text"]].extend(x for x in intermediate if x not in hashtag_network[hashtag["text"]]) #add remaining hashtags if they are missing     

        
        
        # users = [tweet["user"] for tweet in cluster]
        # print(getGroupUserStats(users))

def getClusterStats(cluster):
    users = [tweet["user"] for tweet in cluster]
    importantUsers = {"following": 0, "statuses": 0}
    importantUsers["following"] = max([[user["followers_count"], user["screen_name"]] for user in users])[1]
    importantUsers["statuses"] = max([[user["statuses_count"], user["screen_name"]] for user in users])[1]

    for hashtaglist in [tweet["entities"]["hashtags"] for tweet in cluster if tweet["entities"]["hashtags"]]:
        hashtags = [hashtag["text"] for hashtag in hashtaglist]
    
    for mentionlist in [tweet["entities"]["user_mentions"] for tweet in cluster if tweet["entities"]["user_mentions"]]:
        mentions = [mention["screen_name"] for mention in mentionlist]

    return importantUsers

def getGroupStats(groups):
    return groups.count().agg(['min','max','mean']).to_string(header=False)

def printNet(network):
    for key in network:
        print (key, network[key])

def createGraph(network):
    G = nx.DiGraph()
    for start in network:
        for end in network[start]: 
            G.add_edge(start, end)
    return G
    
def getGraphStats(G):
    #Triads
    triads = nx.algorithms.triads.triadic_census(G)
    desirable_triads = ['021C', '111D', '111U', '030T', '030C', '201', '120D', '120U', '120C', '210', '300']
    strict_triads = [triads[x] for x in desirable_triads]
    print(triads)
    print("Number of triads: %d" %(sum(strict_triads)))
    #Triangles
    print("Number of triangles: %d" %(triads["300"]))
    #Degree
    print("User that gets mentioned the most: ")
    print(sorted(G.in_degree, key=lambda x: x[1], reverse=True)[0])
    print("User that mentions the most other people: ")
    print(sorted(G.out_degree, key=lambda x: x[1], reverse=True)[0])
    print("User that is part of the most mentions: ")
    print(sorted(G.degree, key=lambda x: x[1], reverse=True)[0])

def drawGraph(G):
    # H = nx.DiGraph()
    # H.add_edges_from(G.edges())
    # plt.subplot(121)
    # nx.draw(H, node_size=1, width=0.2)
    # plt.subplot(122)
    nx.draw(G, node_size=1, width=0.2)
    plt.show()


    


# streamData()
groups = clusterData(skipval = 0, limitval=200)
buildClusters(groups)
generateNetwork()
G = createGraph(overall_mention_network)
getGraphStats(G)
# drawGraph(G)