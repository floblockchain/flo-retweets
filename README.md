# Taubenschlag Twitter Bot
## Welcome to FLO Retweets! 
To participate in the campaign please join on https://retweets.floblockchain.com!
## What is it
The FLO version of https://github.com/bithon/Taubenschlag
## How to install
Request a Twitter dev account: https://developer.twitter.com/en/account/environments

A domain routed to the server of the bot

You need a server with Python3 a webserver and a reverse proxy.

Both can be easily provided with apache2:
```
# apt-get install apache2
# apt-get install python-certbot-apache
```
Set the hostname in `/etc/apache2/sites-enabled/000-default` to the public domain name (yes it's port 80)
```
# systemctl restart apache2
# certbot --apache
# systemctl restart apache2
# certbot certonly
```
Follow the certbot wizard.
Add this 2 lines to `file_name_missing`:
```
Code reverse proxy
```
Download FLO Retweets Bot to `/opt` and unzip it. Make the app available in `/opt/flo-retweets`.
```
cd /var/www/html 
ln -s /opt/flo-retweets/html/* .
```
Install requirements:
```
apt install python3-pip
python3 -m pip install -r requirements
```
Create two apps in https://developer.twitter.com/en/account/environments
1. Is the main app with read+write permissions (user auth to this app)
2. Is the DM sending interface app with read+write+dm permissions (user dont know about his app)

Copy the access tokens from the two twitter apps to `./conf.d/secrets.cfg` (use the template in 
`./conf.d/secrets.cfg_empty`).

Modify `./conf.d/main.cfg` if needed.

Modify `./conf.d/rt-level-rule-set.cfg` to setup RT sources.

How to use systemd? TODO

Lets encrypt offers `certbot nenew` to make the renewal easy!

Its important to backup `/opt/flo-retweets/db/flo_retweets_bot.json`, do it with `cat flo_retweets_bot.json > 
backup.json`.

## Report bugs or suggest features
https://github.com/floblockchain/flo-retweets/issues/new/choose
## Todo
- https://github.com/floblockchain/flo-retweets/projects/1
## How to contribute
To contribute follow 
[this guide](https://github.com/floblockchain/flo-retweets/blob/master/CONTRIBUTING.md).
