import tweepy
import os
from dotenv import load_dotenv
import time
import pandas as pd
import numpy as np
import os
import time
import json
from bs4 import BeautifulSoup as bs
from selenium import webdriver
import warnings
from selenium.webdriver.common.by import By
warnings.filterwarnings("ignore")

class GetTwitterBookmark:
    
    """
        This class can be used to pull bookmarks for a user using the Twitter API with a created app.
    
        For this to work, we will need to activate OAuth 2.0 Authorization Code Flow with PKCE. We will need to activate this
        in the developer settings, precisely in the "User authentication settings" section after we create our app.
        
        Some extra info about authentication can be found here: https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code
        
        Of course, we will also need the client id and client secret of our app.
        
        Add the client id and client secret to the .env file (be careful not to upload this file! Do add it to the .gitignore file!).
        The entries in the .env file should look like:
        client-id = "xx"
        client-secret = "xx"
    """
    
    def __init__(self):
        load_dotenv()

        # read keys from .env
        self.client_id = os.getenv('client-id')
        self.client_secret = os.getenv('client-secret')
    
    def fetch_token(self):
        
        """Function to fetch the access token needed to pull bookmarks. Though heavily modified, see https://improveandrepeat.com/2022/07/python-friday-131-working-with-bookmarks-in-tweepy/ for some extra explanations. Credits go to the author for the inspiration
        
        We should have our Twitter username and password handy for this part, as we will need it when the browser pops up
        """
        option = webdriver.ChromeOptions()
        #option.add_argument('--headless')
        option.add_argument('--no-sandbox')
        option.add_argument('--disable-dev-shm-usage')
        option.add_argument('--incognito')
        option.add_argument('--disable-infobars')
        option.add_argument("--disable-notifications")
        option.add_experimental_option("excludeSwitches", ['enable-automation'])

        driver = webdriver.Chrome(options=option)
        driver.implicitly_wait(10)

        baseurl = "https://twitter.com/i/flow/login"

        driver.get(baseurl)

        ### We need to have our Twitter username and password handy. We have 60 seconds to log in manually
        ### Automation of this step was decided against as it was unreliable and a bit slower

        time.sleep(60)
        
        # prepare OAuth2Handler
        oauth2_user_handler = tweepy.OAuth2UserHandler(
            client_id=self.client_id,
            redirect_uri="https://www.twitter.com/oauth/twitter",
            # minimal scope to work with bookmarks
            scope=["bookmark.read", "bookmark.write",
                "tweet.read","users.read"],
            client_secret=self.client_secret
        )
        
        ## Everything below this part, and before the "driver.quit()" must be executed before 30 seconds, or the authorization code will time out. Automation helps us achieve this
        # print(oauth2_user_handler.get_authorization_url())
        auth_link = oauth2_user_handler.get_authorization_url()

        driver.get(auth_link)

        time.sleep(5)
        ### at the point we need to click "Authorize" in the browser. We have 5 seconds

        authorization_response = driver.current_url
        access_token = oauth2_user_handler.fetch_token(
            authorization_response
        )

        ## quit the Selenium driver
        driver.quit()

        # print(f"\naccess-token-pkce={access_token['access_token']}")

        # store the token in the .env file:
        with open(".env", "r") as envfile:
            contents = envfile.readlines()

        contents = [con for con in contents if "access-token-pkce" not in con]
        
        contents = contents + [f"\naccess-token-pkce='{access_token['access_token']}'"]
        with open(".env", "w") as envfile:
            for env_data in contents:
                envfile.write(env_data)
    
    def read_bookmarks(self):
        """Read bookmarks for a user. The maximum that will be read is the most recent 800 bookmarks.
            Also, the read rate is 180 bookmarks per 15 minutes.
            Read more here: https://developer.twitter.com/en/docs/twitter-api/tweets/bookmarks/api-reference/get-users-id-bookmarks
        """
        
        load_dotenv()
 
        # read keys just added to .env file
        access_token_pkce = os.getenv('access-token-pkce')
        users, media, all_bookmarks = {}, {}, {}
        
        client = tweepy.Client(access_token_pkce)

        response = client.get_bookmarks(
            expansions="author_id,attachments.media_keys",
            tweet_fields="created_at,public_metrics,attachments",
            user_fields="username,name,profile_image_url",
            media_fields="public_metrics,url,height,width,alt_text")
        
        tweets = response.data

        ## get users for bookmarks
        for user in response.includes['users']:
            users[user.id] = f"{user.name} (@{user.username}) [{user.profile_image_url}]"

        with open(time.strftime("%Y%m%d_", time.gmtime())+"users_from_bookmarks.json", "w") as usr:
            json.dump(users, usr, indent=4)
            
        ## process media attachment
        if 'media' in response.includes:
            for item in response.includes['media']:
                media[item.media_key] = f"{item.url} - {item.height}x{item.width} - Alt: {item.alt_text} - Type: {item.type}"
                
        with open(time.strftime("%Y%m%d_", time.gmtime())+"media_from_bookmarks.json", "w") as mda:
            json.dump(media, mda, indent=4)
            
        ## process bookmarks
        for tweet in tweets:
            # print('-' * 50)
            tweet_data = tweet.data
            tweet_data["user_name"] = users[tweet.author_id]
            # print(f"{tweet.id} ({tweet.created_at}) - {users[tweet.author_id]}:\n {tweet.text} \n")
            metric = tweet.public_metrics
            # print(f"retweets: {metric['retweet_count']} | likes: {metric['like_count']}")
            if tweet.attachments is not None:
                media_list = [media[media_key] for media_key in tweet.attachments['media_keys']]
                tweet_data["media_attachment"] = media_list
                
            all_bookmarks[tweet.id] = tweet_data
            
        with open(time.strftime("%Y%m%d_", time.gmtime())+"all_bookmarks.json", "w") as bkmrk:
            json.dump(all_bookmarks, bkmrk, indent=4)
            

if __name__ == "__main__":
    twitter_bookmarks = GetTwitterBookmark()
    twitter_bookmarks.fetch_token()
    twitter_bookmarks.read_bookmarks()