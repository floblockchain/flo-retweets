# FLO Retweets Bot Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to 
[Semantic Versioning](http://semver.org/).

## (development stage/unreleased)

## 0.6.1
### Fixed
- Exception handling get timeline and auth denied

## 0.6.0
### Added
- rt sources: https://github.com/floblockchain/flo-retweets/projects/1#card-24147426 to configure in 
  `./conf.d/rt-level-rule-set.cfg`

## 0.5.0
### Added
- forum link (rule-set) to DMs
- get-info (retweets and rt-level)
### Changed
- DM text: https://github.com/floblockchain/flo-retweets/pull/1
- renamed get-info to get-bot-info
### Removed
- unused css code in ./html/css/*
### Fixed
- Typo in DM

## 0.4.0
### Added
- https://github.com/floblockchain/flo-retweets/projects/1#card-24117403
- https://github.com/floblockchain/flo-retweets/projects/1#card-24116742 for get-info
- config setting for DM sender name
- show retweets in the help DM answer
## Changed
- redirect to canceled.html instead of sending an own page

## 0.3.2
### Fixed
- send DM to sys admins on new user auth

## 0.3.1
### Fixed
- KeyError oAuthTwitter/verify

## 0.3.0
### Added
- config setting for webserer listener IP and port
- HTML update
- https://github.com/floblockchain/flo-retweets/projects/1#card-24116742

## 0.2.0
### Added
- Handling for https://github.com/floblockchain/flo-retweets/projects/1#card-24116784 for status DM on new user auth
- https://github.com/floblockchain/flo-retweets/projects/1#card-24119327

## 0.1.0
Initial release