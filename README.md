# Twitter-Crawler
## How to use:
1. Open the main.py file in an editor
2. Check imports and install missing python packages if necessary
3. Exchange the Twitter API keys with your own from [Twitter](developer.twitter.com)
4. Import the database from the sample.csv (although preferably from the sample.json) into your database configuration
5. Change the `client`, `db` and `col` to fit your database configuration
6. Open up a command line interface ("EXECUTE" indicates a switch to the CLI to enter `python main.py`)

### 1. Gathering Data
#### 1.1 Streaming
1. At the bottom of the file, write down `streamData()`
2. EXECUTE

Feel free to add and remove words from `WORDS`

#### 1.2 Rest Probes
1. At the bottom of the file, write down `RESTprobeData()`
2. EXECUTE

Feel free to add and remove words from `keywords`

### 2. Generate and Analyse Cluster Data
1. At the bottom of the file, write down `printClusterData()`
2. EXECUTE

'printClusterData()' takes `limit`, `skip` and `percentage` as optional parameters
* limit: Limit the amount of tweets loaded from db. Default:1000 
* skip: Skip tweets in db before loading. Default:0
* percentage: Set a rough percentage of clusters to be analysed in percent. Default: 10
There are `verbose` parameters for most of the cluster methods. Toggle their values to change what information get printed out.

### 3. Directly Analyse Sample Data
1. At the bottom of the file, write down `printSampleData()`
2. EXECUTE

'printSampleData()' takes `limit`, `skip` and `draw` as optional parameters
* limit: Limit the amount of tweets loaded from db. Default:1000 
* skip: Skip tweets in db before loading. Default:0
* draw: Set to True to draw graphs for the mention- and hashtag network. Default: False
There are `verbose` parameters for most of the sample methods. Toggle their values to change what information get printed out.

## Additional Sources and References:
#### https://www.toptal.com/python/twitter-data-mining-using-python
#### http://docs.tweepy.org/en/latest/streaming_how_to.html
#### https://medium.com/@adam.oudad/stream-tweets-with-tweepy-in-python-99e85b6df468
#### https://github.com/qcrisw/tweet-crawler/blob/master/databases.py
#### https://networkx.github.io/documentation/stable/
