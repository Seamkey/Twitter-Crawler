import sys
import tweepy
import pymongo
import json
import time
from random import randint
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import pandas as pd

import networkx as nx
import matplotlib.pyplot as plt

#These are no longer active Keys: please insert your own from developer.twitter.com
consumer_key = "4vT6TFI7yIdtNsypX17Z163th"
consumer_secret = "v9OgxdEy25mELUU9JOU1k8FsfGtHQOBEDlx3V51oauOzzsqZxz"
access_token = "1227215889461846017-KBoPxWlnrJZ3SZoC9VmedcOG5laF68"
access_token_secret = "bOm10DTuJ2JytBKI1911tVpMCzNMH8pJSDLKcGPl2ZYHQ"

#switch these out to whichever configuration is necessary
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["Twitter-Data"]
col = db["Tweets"]
#END Setup --------------------------------------------------------------------------------------

#BEGIN Data Crawl -------------------------------------------------------------------------------
# overwriting tweepy StreamListener class
class Listener(tweepy.StreamListener):

    def __init__(self):
        super(Listener, self).__init__()

    def on_data(self, data):
        col.insert_one(json.loads(data))

    def on_error(self, status_code):
        print(status_code)
        return False

# start streaming data
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
    except KeyboardInterrupt:
        print('Stream stopped')
    finally:
        print('Done')
        stream.disconnect()

#probe for particular keywords
def RESTprobeData():
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit_notify=True, wait_on_rate_limit=True)
    print("ready")

    keywords = ['#coronavirus', '#COVID19', '#DSTMVCA', '#AMVCA7', '#TachaXAMVCA', ]
    num_dupes = 0
    try:
        for keyword in keywords:
            for status in tweepy.Cursor(api.search, q=keyword).items():
                tweet = json.loads(json.dumps(status._json))
                tweet["_id"] = tweet["id"]
                try:
                    col.insert_one(tweet)
                except pymongo.errors.DuplicateKeyError:
                    num_dupes = num_dupes + 1
    except KeyboardInterrupt:
        print("Interrupted")
        pass
    print("Number of ignored duplicate tweets: %d" %(num_dupes))
#END Data Crawl ---------------------------------------------------------------------------------


#BEGIN Graph helper functions -------------------------------------------------------------------
#create a networkx graph from a dictionary of vertices
def createGraph(network):
    G = nx.DiGraph()
    for start in network:
        for end in network[start]: 
            G.add_edge(start, end)
    return G
    
#gather network statistics on a given graph
def getGraphStats(G, verbose=False):
    #Ties
    edges = G.number_of_edges()
    #Triads
    triads = nx.algorithms.triads.triadic_census(G)
    desirable_triads = sum([triads[x] for x in ['021C', '111D', '111U', '030T', '030C', '201', '120D', '120U', '120C', '210', '300']])
    #Triangles
    triangles = triads["300"]
    #Degree centrality
    most_in = sorted(G.in_degree, key=lambda x: x[1], reverse=True)[0]
    most_out = sorted(G.out_degree, key=lambda x: x[1], reverse=True)[0]
    highest_degree = sorted(G.degree, key=lambda x: x[1], reverse=True)[0]
    #Closeness centrality
    most_central = sorted(nx.closeness_centrality(G), key=lambda x: x[1], reverse=True)[0]

    if verbose:
        print("Number of ties: %d" %(edges))
        print("Number of triads: %d" %(desirable_triads))
        print("Number of triangles: %d" %(triangles))
        print("Highest in-degree: %s %s" %(most_in))
        print("Highest out-degree: %s %s" %(most_out))
        print("Highest degree: %s %s" %(highest_degree))
        print("Highest closeness centrality: %s" %(most_central))

    return {
        "edges": edges,
        "triads": triads,
        "triangles": triangles,
        "most_in": most_in,
        "most_out": most_out,
        "highest_degree": highest_degree,
        "most_central": most_central
    }

#draw a griven graph
def drawGraph(G, labels=False):
    nx.draw(G, node_size=1, with_labels=labels, width=0.2)
    plt.show()
#END Graph helper functions ---------------------------------------------------------------------


#BEGIN Cluster Generation and Analysis ----------------------------------------------------------
#gather statistics on all clusters
def getGroupStats(groups):
    return groups.count().agg(['min','max','mean']).to_string(header=False)

#cluster data from the database using sklearn k means algorithm
def clusterData(limit = 1000, skip = 0, verbose = False):
    fetchResult = col.find({}, {"text":1}).skip(skip).limit(limit)
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
    number_tweets = len(tweets)
    k = int((number_tweets * 0.1))
    model = KMeans(n_clusters=k, max_iter=300, verbose=0)
    model.fit(vectorizer.fit_transform(tweets))
    groups = pd.DataFrame({"group": model.labels_, "tweetID": ids}).groupby(["group"])
    
    #generate list of clusters with user and entity information from groups of ids
    clusters = []
    idClusters = [group["tweetID"].tolist() for _, group in groups]
    for cluster in idClusters:
        clusters.append([col.find_one({"_id": ID}, {"_id": 0, "user": 1, "entities": 1}) for ID in cluster])
    
    if verbose:
        print(getGroupStats(groups))
        print("Number of tweets: %d" %(number_tweets))
        print("Number of clusters: %d" %(k))
    return clusters

#gather statistics on a given cluster                
def getClusterStats(cluster, verbose=False):
    cluster_size = len(cluster)
    users = [tweet["user"] for tweet in cluster]
    most_followers, mostFol = max([[user["followers_count"], user["screen_name"]] for user in users])
    most_statuses, mostStat = max([[user["statuses_count"], user["screen_name"]] for user in users])

    hashtags = []
    for hashtaglist in [tweet["entities"]["hashtags"] for tweet in cluster if tweet["entities"]["hashtags"]]:
        hashtags = [hashtag["text"] for hashtag in hashtaglist]
    try:
        best_hashtag = max(set(hashtags), key=hashtags.count)
    except ValueError:
        best_hashtag = "- None -"
    

    if verbose:
        print("cluster_size: %d" %(cluster_size))
        print("The user with the most followers is %s with %d followers." %(mostFol, most_followers))
        print("The user with the most posts is %s with %d posts." %(mostStat, most_statuses))
        print("The most popular hashtag is: %s" %(best_hashtag))

    return {
        "cluster_size": cluster_size,
        "most_followers": most_followers,
        "most_followed": mostFol,
        "most_statuses": most_statuses,
        "most_postings": mostStat,
        "best_hashtag": best_hashtag
    }

#chose a random number of clusters with a given probability and gather metrics on those clusters
def parseClusters(clusters, verbose=False, graph_info = False, sample_probability = 10):
    same_user = 0
    selected_clusters = 0
    for cluster in clusters:  
        mention_network = {}
        hashtag_network = {}          
        #random cluster selection
        if randint(1, 100000) <= sample_probability*1000:
            print()
            selected_clusters = selected_clusters + 1
            for tweet in cluster:
                user = tweet["user"]

                #mention statistics
                mentions = tweet["entities"]["user_mentions"]
                if mentions:
                    key = "screen_name"
                    if not user[key] in mention_network:
                        mention_network[user[key]] = []
                    for mention in mentions:
                        if mention[key] not in mention_network[user[key]]:
                            mention_network[user[key]].append(mention[key])
                
                #hashtag statistics
                hashtags = tweet["entities"]["hashtags"]
                if hashtags:
                    key = "text"
                    for hashtag in hashtags:
                        intermediate = [x[key] for x in hashtags if x[key] != hashtag[key]] #hashtag list without the current hashtag
                        if intermediate:
                            if not hashtag[key] in hashtag_network:
                                hashtag_network[hashtag[key]] = []
                            hashtag_network[hashtag[key]].extend(x for x in intermediate if x not in hashtag_network[hashtag[key]]) #add remaining hashtags if they are missing  

            cluster_stats = getClusterStats(cluster, verbose = verbose)
            if cluster_stats["most_followed"] == cluster_stats["most_postings"]:
                same_user = same_user + 1
            if mention_network:
                mention_stats = getGraphStats(createGraph(mention_network), verbose = graph_info)
                print("The most mentioned user is: %s mentioned %s times" %(mention_stats["most_in"]))
            if hashtag_network:
                hashtag_stats = getGraphStats(createGraph(hashtag_network), verbose = graph_info)
                print("The hashtag that occurred with most other hashtags is: %s %s times" %(hashtag_stats["highest_degree"]))

    if verbose:
        print()
        print("Number of selected clusters: %d" %(selected_clusters))
        print("Number of clusters where user with most followers equals user with most statuses: %d" %(same_user))

#print metrics gathered on various clusters
def printClusterData(limit = 1000, skip = 0, percentage = 10):
    clusters = clusterData(limit = limit, skip = skip, verbose = True)
    parseClusters(clusters, verbose=True, sample_probability = percentage)
#END Cluster Generation and Analysis ------------------------------------------------------------


#BEGIN Sample Analysis --------------------------------------------------------------------------
#fetch a sample of tweets from the database as a list
def fetchList(limit = 0, skip = 0):
    return list(col.find({}, {"_id": 0}).skip(skip).limit(limit))

#sort values in list data according to second element and return top X entries
def getTopX(data, X):
    return sorted(data, key = lambda x: x[1], reverse=True)[0:X]

#print a list entry by entry
def printList(data):
    for entry in data:
        print(entry)

#gather metrics on sample
def parseSample(tweets, verbose=False):
    #metrics to be gathered
    mention_network = {} #userA: [therealdonaldtrump, bbc, ...]
    hashtag_network = {} #Corona: [coronavirus, COVID-19, ...]
    hashtag_frequencies = {} #Corona: 120
    numTweetsWithExtended = 0

    #tracks checked users
    user_list = []
    #structure: (name, count)
    followers = []
    friends = []
    statuses = []
    favourites = []
    #other user stats
    usersWurl = 0
    verified = 0

    for tweet in tweets:
        #tweet statistics
        try:
            if tweet["extended_entities"]:
                numTweetsWithExtended = numTweetsWithExtended + 1
        except KeyError:
            pass

        #user statistics
        try:
            user = tweet["user"]
            if not user["id_str"] in user_list:
                user_list.append(user["id_str"])
                followers.append((user["name"], user["followers_count"]))
                friends.append((user["name"], user["friends_count"]))
                statuses.append((user["name"], user["statuses_count"]))
                favourites.append((user["name"], user["favourites_count"]))

                if user["url"]:
                    usersWurl = usersWurl + 1
                if user["verified"]:
                    verified = verified + 1
        except KeyError:
            pass
        
        #mention statistics
        try:
            mentions = tweet["entities"]["user_mentions"]
            if mentions:
                key = "screen_name"
                #expand mention network
                if not user[key] in mention_network:
                    mention_network[user[key]] = []
                for mention in mentions:
                    mention_network[user[key]].append(mention[key])
        except KeyError:
            pass

        #hashtag statistics
        try:
            hashtags = tweet["entities"]["hashtags"]
            if hashtags:
                key = "text"
                for hashtag in hashtags:
                    #expand hashtag network
                    intermediate = [x[key] for x in hashtags if x[key] != hashtag[key]] #hashtag list without the current hashtag
                    if intermediate:
                        if not hashtag[key] in hashtag_network:
                            hashtag_network[hashtag[key]] = []
                        hashtag_network[hashtag[key]].extend(x for x in intermediate if x not in hashtag_network[hashtag[key]]) #add remaining hashtags if they are missing     
                    #get frequencies of hashtags
                    if not hashtag[key] in hashtag_frequencies:
                        hashtag_frequencies[hashtag[key]] = 1
                    else:
                        hashtag_frequencies[hashtag[key]] = hashtag_frequencies[hashtag[key]] + 1
        except KeyError:
            pass

    X = 5
    hashtag_frequencies = getTopX(hashtag_frequencies.items(), X)
    followers = getTopX(followers, X)
    friends = getTopX(friends, X)
    statuses = getTopX(statuses, X)
    favourites = getTopX(favourites, X)
    #users that mention the same people the most
    same_mentions = sorted({user: getTopX(Counter(
        mention_network[user]).items(), 1)[0] for user in mention_network}.items(),
        key= lambda x: x[1][1],
        reverse=True)[0:X]

    num_tweets = len(tweets)
    num_users = len(user_list)

    if verbose:
        print("Number of tweets in the sample: %d" %(num_tweets))
        print("Number of users in the sample: %d" %(num_users))
        print("Number of tweets with extended entities: %d" %(numTweetsWithExtended))
        print("Number of users with an URL: %d" %(usersWurl))
        print("Number of verified users: %d" %(verified))
        print()
        print("Most frequently used hashtags: ")
        printList(hashtag_frequencies)
        print()
        print("Users with most followers: ")
        printList(followers)
        print()
        print("Users with most friends: ")
        printList(friends)
        print()
        print("Users with most statuses: ")
        printList(statuses)
        print()
        print("Users with most favourites: ")
        printList(favourites)
        print()
        print("Users that mention the same user the most: ")
        printList(same_mentions)
        print()

    return {
        "mention_network": mention_network,
        "hashtag_network": hashtag_network,
        "hashtag_frequencies": hashtag_frequencies,
        "tweetsExtendedEntities": numTweetsWithExtended,
        "followers": followers,
        "friends": friends,
        "statuses": statuses,
        "favourites": favourites,
        "same_mentions": same_mentions,
        "usersURL": usersWurl,
        "verified": verified,
        "tweets": num_tweets,
        "users": num_users
    }

#print metrics gathered on sample and draw created networks
def printSampleData(limit = 1000, skip = 0, draw = False):
    tweets = fetchList(skip = skip, limit = limit)
    results = parseSample(tweets, verbose=True)
    
    mention_graph = createGraph(results["mention_network"])
    mention_stats = getGraphStats(mention_graph, verbose = True)
    print("The most mentioned user is: %s, mentioned %s times" %(mention_stats["most_in"]))

    hashtag_graph = createGraph(results["hashtag_network"])
    hashtag_stats = getGraphStats(hashtag_graph, verbose = True)
    print("The hashtag that occurred with most other hashtags is: %s %s times" %(hashtag_stats["highest_degree"]))
    if draw:
        drawGraph(mention_graph)
        drawGraph(hashtag_graph)
#END Sample Analysis ----------------------------------------------------------------------------

