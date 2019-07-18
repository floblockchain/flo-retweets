#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# File: flo_retweets_bot.py
#
# Part of ‘FLO Retweets Bot’
# Project website: https://retweets.floblockchain.com/
# GitHub: https://github.com/floblockchain/flo-retweets
#
# Author: Oliver Zehentleitner
#         https://about.me/oliver_zehentleitner/
#
# Copyright (c) 2019, floblockchain Team (https://github.com/floblockchain)
# All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from __future__ import print_function
from cheroot import wsgi
from copy import deepcopy
from flask import Flask, redirect, request
from shutil import copyfile
from argparse import ArgumentParser
import argparse
import configparser
import datetime
import logging
import json
import os
import textwrap
import threading
import time
import tweepy

logging.basicConfig(format="{asctime} [{levelname:8}] {process} {thread} {module} {pathname} {lineno}: {message}",
                    filename='flo_retweets_bot.log',
                    style="{")
logging.getLogger(__name__).addHandler(logging.StreamHandler())
logging.getLogger(__name__).setLevel(logging.DEBUG)


class FloRetweetBot(object):
    def __init__(self):
        self.app_version = "0.3.0"
        self.config = self._load_config()
        self.error_text = "Something went wrong! Please <a href='" + self.config['SYSTEM']['base_url'] + \
                          "oAuthTwitter/start'>try again</a> or report to " \
                          "<a href='https://twitter.com/" + self.config['SYSTEM']['admin_contact_twitter_account'] + \
                          "'>" + self.config['SYSTEM']['admin_contact_twitter_account'] + "</a>!"
        self.consumer_key = self.config['SECRETS']['consumer_key']
        self.consumer_secret = self.config['SECRETS']['consumer_secret']
        self.access_token = self.config['SECRETS']['access_token']
        self.access_token_secret = self.config['SECRETS']['access_token_secret']
        self.consumer_key_dm = self.config['SECRETS']['consumer_key_dm']
        self.consumer_secret_dm = self.config['SECRETS']['consumer_secret_dm']
        self.access_token_dm = self.config['SECRETS']['access_token_dm']
        self.access_token_secret_dm = self.config['SECRETS']['access_token_secret_dm']
        self.app_name = self.config['SYSTEM']['app_name']
        self.base_url = self.config['SYSTEM']['base_url']
        parser = ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                description=textwrap.dedent(self.app_name + " " + self.app_version+ " by "
                                                            "\r\n - Oliver Zehentleitner (2019 - 2019)"
                                                            "\r\n\r\n"
                                                            "description: this bot manages retweets for the FLO "
                                                            "Twitter community of multiple accounts!"),
                                epilog=textwrap.dedent("GitHub: https://github.com/floblockchain/flo-retweets"))
        parser.add_argument('-a', '--account-list', dest='account_list',
                            help='show saved account list', action="store_true")
        self.parsed_args = parser.parse_args()
        self.api_self = False
        self.refresh_api_self()
        self.api_dm = False
        self.refresh_api_dm()
        self.data = False
        self.data_layout = {"tweets": [],
                            "accounts": {},
                            "statistic": {"tweets": 0,
                                          "retweets": 0,
                                          "sent_help_dm": 0,
                                          "received_botcmds": 0}}
        self.bot_user_id = self.api_self.get_user(self.config['SYSTEM']['bot_twitter_account']).id
        self.sys_admin_list = self.config['SYSTEM']['sys_admin_list'].split(",")
        self.load_db()
        print("Starting " + str(self.app_name) + " " + str(self.app_version))

    def _load_config(self):
        config_path = "./conf.d"
        config = configparser.ConfigParser()
        if os.path.isdir(config_path) is False:
            logging.critical("can not access " + config_path)
            return False
        raw_file_list = os.listdir(config_path)
        for file_name in raw_file_list:
            if os.path.splitext(file_name)[1] == ".cfg":
                try:
                    config.read_file(open(config_path + "/" + file_name))
                except ValueError as error_msg:
                    logging.error(str(error_msg))
                    return False
        return config

    def _webserver_thread(self):
        logging.debug("starting webserver ...")
        app = Flask(__name__)

        @app.route('/oAuthTwitter/start')
        def oauth_twitter_start(consumer_key=self.consumer_key, consumer_secret=self.consumer_secret):
            auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
            try:
                return redirect(auth.get_authorization_url(), code=302)
            except tweepy.TweepError as error_msg:
                logging.error('failed to get request token. ' + str(error_msg))

        @app.route('/oAuthTwitter/verify')
        def oauth_twitter_verify():
            try:
                if request.args["denied"]:
                    return redirect(self.config['SYSTEM']['redirect_canceled'], code=302)
            except KeyError:
                pass
            auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
            auth.request_token = {'oauth_token': request.args["oauth_token"],
                                  'oauth_token_secret': request.args["oauth_verifier"]}
            try:
                auth.get_access_token(request.args["oauth_verifier"])
            except tweepy.TweepError as error_msg:
                logging.error('failed to get access token. ' + str(error_msg))
                return self.error_text

            if auth.access_token_secret is not None and auth.access_token is not None:
                status = False
                user = self.api_self.get_user(screen_name=auth.get_username())
                try:
                    if len(self.data['accounts']) > 0:
                        status = True
                except TypeError:
                    pass
                if status is False:
                    self.data['accounts'] = {str(user.id): {}}
                self.data['accounts'][str(user.id)] = {'access_token': str(auth.access_token),
                                                       'access_token_secret': str(auth.access_token_secret),
                                                       'retweet_level': 2}
                self.save_db()
                logging.info("saved new oAuth access of twitter user " + str(user.name) + "!")
                print("Saved new oAuth token of @" + str(user.screen_name) + " (" + str(user.name) + ")!")
                retweet_level = self.data['accounts'][str(user.id)]['retweet_level']
                api = self.get_api_user(user.id)
                try:
                    api.create_friendship(id=self.bot_user_id)
                except tweepy.error.TweepError as error_msg:
                    if "You can't follow yourself" in str(error_msg):
                        pass
                    else:
                        logging.error(str(error_msg))
                try:
                    self.api_self.create_friendship(id=user.id)
                except tweepy.error.TweepError as error_msg:
                    if "You can't follow yourself" in str(error_msg):
                        pass
                    else:
                        logging.error(str(error_msg))
                try:
                    self.api_self.send_direct_message(user.id, "Hello " + str(user.name) +
                                                      "!\r\n\r\nThank you for joining us!\r\n\r\n"
                                                      "This app is a BETA version, please report issues to "
                                                      "@UNICORN_OZ - Thank you!\r\n\r\n"
                                                      "If you wish to disable the access of our app, please visit "
                                                      "https://twitter.com/settings/applications and remove the "
                                                      "authorization!\r\n\r\n"
                                                      "Once the authorization is disabled, we are going to delete your "
                                                      "access token from our system and it wont work anymore if you "
                                                      "enable the access again. In such a case you would have to "
                                                      "authorize the app again on "
                                                      "twitter:\r\n" + self.base_url + "/oAuthTwitter/start"
                                                      "\r\n\r\nTo subscribe to a retweet"
                                                      "-level please write a DM with the text:\r\n"
                                                      "- 'set-rt-level:1' to retweet only first class posts\r\n"
                                                      "- 'set-rt-level:2' to be informative\r\n"
                                                      "- 'set-rt-level:3' to retweet everything what this app "
                                                      "finds for you (related to FLO!)\r\n\r\nYour current "
                                                      "retweet-level is " + str(retweet_level) + "!\r\n\r\nFor further "
                                                      "information write a direct message with the text 'help' to me "
                                                      "@" + str(self.config['SYSTEM']['bot_twitter_account']) + "!"
                                                      "\r\n\r\nBest regards,\r\nthe FLO community!")
                    # send status message to bot account
                    self.send_status_message_new_user(self.bot_user_id, user.id)
                    # send status message to sys_admins
                    for user_name in self.sys_admin_list:
                        self.send_status_message_new_user(self.api_self.get_user(user_name).id, user.id)

                except tweepy.error.TweepError:
                    pass
                return redirect(self.config['SYSTEM']['redirect_successfull_participation'], code=302)
                # return "Thank you for participation!<br><br>Go back to <a href='https://www.twitter.com'>Twitter</a>!"
            else:
                return self.error_text
        try:
            dispatcher = wsgi.PathInfoDispatcher({'/': app})
            webserver = wsgi.WSGIServer((self.config['SYSTEM']['api_listener_ip'],
                                         int(self.config['SYSTEM']['api_listener_port'])),
                                        dispatcher)
            webserver.start()
        except RuntimeError as error_msg:
            logging.critical("webserver is going down! " + str(error_msg))

    def send_status_message_new_user(self, recipient_id, new_user_id):
        self.api_self.send_direct_message(recipient_id,
                                          "Hello " + str(self.api_self.get_user(recipient_id).screen_name) + "!\r\n\r\n"
                                          "A new user subscribed to FLO Retweets: " + str(new_user_id) + " - " +
                                          str(self.api_self.get_user(recipient_id).screen_name) +
                                          "\r\n\r\nBest regards,\r\nthe FLO community!")

    def check_direct_messages(self):
        time.sleep(2)
        while True:
            try:
                dm_list = self.api_dm.list_direct_messages()
                for dm in reversed(dm_list):
                    if "".join(str(dm.message_create['message_data']['text']).split()).lower() == "help":
                        print("Send help DM to " + str(dm.message_create['sender_id']) + "!")
                        user = self.api_self.get_user(dm.message_create['sender_id'])
                        user_id = dm.message_create['sender_id']
                        try:
                            retweet_level = self.data['accounts'][str(user_id)]['retweet_level']
                        except KeyError:
                            self.data['accounts'][str(user_id)]['retweet_level'] = 2
                            retweet_level = self.data['accounts'][str(user_id)]['retweet_level']
                        self.api_self.send_direct_message(dm.message_create['sender_id'],
                                                          "Hello " + str(user.name) + "!\r\n\r\n"
                                                          "This app is a BETA version, please report issues to "
                                                          "@UNICORN_OZ - Thank you!\r\n\r\n"
                                                          "If you wish to disable the access of our app, "
                                                          "please visit https://twitter.com/settings/applications and "
                                                          "remove the authorization!"
                                                          "\r\n\r\nOnce the authorization is disabled, we are going "
                                                          "to delete your access token from our system and it wont "
                                                          "work anymore if you enable the access again. In such a "
                                                          "case you would have to authorize the app again on twitter:"
                                                          "\r\n" + self.base_url + "/oAuthTwitter/start"
                                                          "\r\n\r\nTo subscribe to a retweet"
                                                          "-level please write a DM with the text:\r\n"
                                                          "- 'set-rt-level:1' to retweet only first class posts\r\n"
                                                          "- 'set-rt-level:2' to be informative\r\n"
                                                          "- 'set-rt-level:3' to retweet everything what this app "
                                                          "finds for you (related to FLO!)\r\n\r\nYour current "
                                                          "retweet-level is " + str(retweet_level) + "!\r\n\r\n"
                                                          "For further "
                                                          "information write a direct message with the text 'help' to "
                                                          "me @" + str(self.config['SYSTEM']['bot_twitter_account']) +
                                                          "!\r\n\r\nBest "
                                                          "regards,\r\nthe FLO community!")
                        self.api_dm.destroy_direct_message(dm.id)
                        self.data['statistic']['sent_help_dm'] += 1
                        self.save_db()
                    elif "".join(str(dm.message_create['message_data']['text']).split()).lower() == "set-rt-level:1":
                        print("Set retweet_level for user " + str(dm.message_create['sender_id'] + " to 1!"))
                        user = self.api_self.get_user(dm.message_create['sender_id'])
                        user_id = dm.message_create['sender_id']
                        try:
                            self.data['accounts'][str(user_id)]['retweet_level'] = 1
                        except KeyError as error_msg:
                            logging.error("cant execute set-rt-level, because the user.id (" + str(user_id) + ") is "
                                          "not saved in our DB! - " + str(error_msg))
                            self.api_dm.destroy_direct_message(dm.id)
                            continue
                        retweet_level = self.data['accounts'][str(user_id)]['retweet_level']
                        self.api_self.send_direct_message(dm.message_create['sender_id'],
                                                          "Hello " + str(user.name) +
                                                          "!\r\n\r\nYour new retweet-level is " + str(retweet_level) +
                                                          "!\r\n\r\nBest regards,\r\nthe FLO community!")
                        self.api_dm.destroy_direct_message(dm.id)
                        self.data['statistic']['received_botcmds'] += 1
                        self.save_db()
                    elif "".join(str(dm.message_create['message_data']['text']).split()).lower() == "set-rt-level:2":
                        print("Set retweet_level for user " + str(dm.message_create['sender_id'] + " to 2!"))
                        user = self.api_self.get_user(dm.message_create['sender_id'])
                        user_id = dm.message_create['sender_id']
                        try:
                            self.data['accounts'][str(user_id)]['retweet_level'] = 2
                        except KeyError as error_msg:
                            logging.error("cant execute set-rt-level, because the user.id (" + str(user_id) + ") is "
                                          "not saved in our DB! - " + str(error_msg))
                            self.api_dm.destroy_direct_message(dm.id)
                            continue
                        retweet_level = self.data['accounts'][str(user_id)]['retweet_level']
                        self.api_self.send_direct_message(dm.message_create['sender_id'],
                                                          "Hello " + str(user.name) +
                                                          "!\r\n\r\nYour new retweet-level is " + str(retweet_level) +
                                                          "!\r\n\r\nBest regards,\r\nthe FLO community!")
                        self.api_dm.destroy_direct_message(dm.id)
                        self.data['statistic']['received_botcmds'] += 1
                        self.save_db()
                    elif "".join(str(dm.message_create['message_data']['text']).split()).lower() == "set-rt-level:3":
                        print("Set retweet_level for user " + str(dm.message_create['sender_id'] + " to 3!"))
                        user = self.api_self.get_user(dm.message_create['sender_id'])
                        user_id = dm.message_create['sender_id']
                        try:
                            self.data['accounts'][str(user_id)]['retweet_level'] = 3
                        except KeyError as error_msg:
                            logging.error("cant execute set-rt-level, because the user.id (" + str(user_id) + ") is "
                                          "not saved in our DB! - " + str(error_msg))
                            self.api_dm.destroy_direct_message(dm.id)
                            continue
                        retweet_level = self.data['accounts'][str(user_id)]['retweet_level']
                        self.api_self.send_direct_message(dm.message_create['sender_id'],
                                                          "Hello " + str(user.name) +
                                                          "!\r\n\r\nYour new retweet-level is " + str(retweet_level) +
                                                          "!\r\n\r\nBest regards,\r\nthe FLO community!")
                        self.api_dm.destroy_direct_message(dm.id)
                        self.data['statistic']['received_botcmds'] += 1
                        self.save_db()
                    elif "".join(str(dm.message_create['message_data']['text']).split()).lower() == "get-info":
                        user = self.api_self.get_user(dm.message_create['sender_id'])
                        if str(user.id) == str(self.bot_user_id) or str(user.id) == str("1076914789") or \
                                str(user.id) == str("964500628914491394"):
                            print("Send bot infos to " + str(user.id) + " - " + str(user.screen_name))
                            msg = ""
                            msg += "Bot: " + self.app_name + " " + self.app_version + "\r\n"
                            msg += "Accounts: " + str(len(self.data['accounts'])) + "\r\n"
                            for user_id in self.data['accounts']:
                                user = self.api_self.get_user(user_id)
                                msg += "\t" + str(user_id) + " - @" + user.screen_name + " - RT level: " + \
                                       str(self.data['accounts'][user_id]['retweet_level']) + "\r\n"
                            msg += "Tweets: " + str(self.data['statistic']['tweets']) + "\r\n"
                            msg += "Retweets: " + str(self.data['statistic']['retweets']) + "\r\n"
                            msg += "Sent help DMs: " + str(self.data['statistic']['sent_help_dm']) + "\r\n"
                            msg += "Executed bot commands: " + str(self.data['statistic']['received_botcmds'])

                            self.api_self.send_direct_message(dm.message_create['sender_id'],
                                                              "Hello " +
                                                              str(self.api_self.get_user(
                                                                  dm.message_create['sender_id']).name) +
                                                              "!\r\n\r\n" +
                                                              str(msg) + "\r\n\r\nBest regards,\r\nthe FLO community!")
                            self.data['statistic']['received_botcmds'] += 1
                        else:
                            logging.info("Received 'get-info' from unauthorized account: " + str(user.id) + " - " +
                                         str(user.screen_name))
                            print("Received 'get-info' from unauthorized account: " + str(user.id) + " - " +
                                  str(user.screen_name))
                        self.api_dm.destroy_direct_message(dm.id)
            except tweepy.error.RateLimitError as error_msg:
                logging.error(str(error_msg))
                time.sleep(300)
            except tweepy.error.TweepError as error_msg:
                logging.critical(str(error_msg))
            time.sleep(70)

    def get_api_user(self, user_id):
        auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        auth.set_access_token(self.data['accounts'][str(user_id)]['access_token'],
                              self.data['accounts'][str(user_id)]['access_token_secret'])
        api = tweepy.API(auth)
        return api

    def load_db(self):
        try:
            os.remove("./db/" + self.config['DATABASE']['db_file'] + "_backup")
        except FileNotFoundError:
            pass
        try:
            copyfile("./db/" + self.config['DATABASE']['db_file'],
                     "./db/" + self.config['DATABASE']['db_file'] + "_backup")
        except FileNotFoundError:
            pass
        try:
            with open("./db/" + self.config['DATABASE']['db_file'], 'r') as f:
                try:
                    self.data = json.load(f)
                except json.decoder.JSONDecodeError as error_msg:
                    logging.error(str(error_msg) + " - creating new db!")
                    self.data = self.data_layout
        except FileNotFoundError as error_msg:
            logging.error("create new db!" + str(error_msg))
            self.data = self.data_layout

    def refresh_api_self(self):
        auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        auth.set_access_token(self.access_token, self.access_token_secret)
        self.api_self = tweepy.API(auth)

    def refresh_api_dm(self):
        auth = tweepy.OAuthHandler(self.consumer_key_dm, self.consumer_secret_dm)
        auth.set_access_token(self.access_token_dm, self.access_token_secret_dm)
        self.api_dm = tweepy.API(auth)

    def save_db(self):
        try:
            with open("./db/" + self.config['DATABASE']['db_file'], 'w+') as f:
                json.dump(self.data, f)
        except PermissionError as error_msg:
            print("ERROR!!! Can not save database file!")
            logging.critical("can not save database file! " + str(error_msg))

    def search_and_retweet(self):
        while True:
            print("======================================================================================")
            print("Starting new round at " + str(datetime.datetime.now()))
            timeline = self.api_self.user_timeline('FLOblockchain')
            for tweet in timeline:
                tweet_is_retweeted = False
                try:
                    if tweet.id in self.data['tweets']:
                        tweet_is_retweeted = True
                except TypeError:
                    pass
                if tweet_is_retweeted is False:
                    print(str(tweet.id) + " - " + str(tweet.text[0:80]).splitlines()[0] + " ...")
                    self.data['statistic']['tweets'] += 1
                    accounts = deepcopy(self.data['accounts'])
                    for user_id in accounts:
                        if str(user_id) != str(self.bot_user_id) or \
                                self.config['SYSTEM']['let_bot_account_retweet'] == "True":
                            api = self.get_api_user(user_id)
                            try:
                                user_tweet = api.get_status(tweet.id)
                                if not user_tweet.retweeted:
                                    try:
                                        user_tweet.retweet()
                                        print("\tRetweeted:", user_id, str(self.api_self.get_user(user_id).screen_name))
                                        self.data['statistic']['retweets'] += 1
                                    except tweepy.TweepError as error_msg:
                                        print("\tERROR: " + str(error_msg))
                                        logging.error("can not retweet: " + str(error_msg))
                            except tweepy.error.TweepError as error_msg:
                                if "Invalid or expired token" in str(error_msg):
                                    logging.info("invalid or expired token, going to remove user " + user_id)
                                    print("\tERROR: Invalid or expired token, going to remove user " + user_id)
                                    del self.data['accounts'][user_id]
                                    self.save_db()
                    try:
                        self.data['tweets'].append(tweet.id)
                    except AttributeError:
                        self.data["tweets"] = [tweet.id]
                    self.save_db()
            print("Accounts: " + str(len(self.data['accounts'])))
            if self.parsed_args.account_list:
                for twitter_id in self.data['accounts']:
                    user = self.api_self.get_user(twitter_id)
                    print("\t" + str(twitter_id) + "\t@" + user.screen_name + "       \tRT level: " +
                          str(self.data['accounts'][twitter_id]['retweet_level']))
            print("Tweets: " + str(self.data['statistic']['tweets']))
            print("Retweets: " + str(self.data['statistic']['retweets']))
            print("Sent help DMs: " + str(self.data['statistic']['sent_help_dm']))
            print("Executed bot commands: " + str(self.data['statistic']['received_botcmds']))
            print("--------------------------------------------------------------------------------------")
            time.sleep(60)

    def start_bot(self):
        self.start_thread(self.search_and_retweet)
        self.start_thread(self.check_direct_messages)

    def start_thread(self, function):
        thread = threading.Thread(target=function)
        thread.start()

    def start_webserver(self):
        self.start_thread(self._webserver_thread)


flo_retweet_bot = FloRetweetBot()
flo_retweet_bot.start_webserver()
flo_retweet_bot.start_bot()

