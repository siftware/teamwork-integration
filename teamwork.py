#!/usr/bin/env python 

"""
usage: teamwork [-h] [--hotfix] [--reconfigure] task id or url

Checkout a ticket branch

positional arguments:
  task id (or url)  Ticket ID, either as an number or a teamwork url (eg
                    http://projects.siftware.com/tasks/[TASKID])

optional arguments:
  -h, --help        show this help message and exit
  --hotfix          If creating a branch, do it as a hotfix (default is
                    Feature)
  --reconfigure     Setup teamwork configuration (default on first launch)
"""

## To play this game you will need
## Git
## Python
## The pythongit module:
##  `sudo -H pip install gitpython`
## (If this doesn't work, you may need to install/update python. 
##     Linux users shouldn't have a problem, OS users should use homebrew. Requires python > 2.7 < 3.0)
##
## Installation: From this directory: ln -s $HOME/bin/teamwork $PWD/teamwork.py
##
## Blame: Nicholas.Avenell@Siftware.com

import urllib2, base64, json, re, sys

from git import *

from pprint import pprint

import argparse, ConfigParser

from os.path import expanduser

def slugify(s):
    """
    Simplifies ugly strings into something URL-friendly.
    >>> print slugify("[Some] _ Article's Title--")
    some-articles-title

    Adapted from http://dolphm.com/slugify-a-string-in-python/
    """

    s = s.lower()
    for c in [' ', '-', '.', '/']:
        s = s.replace(c, '_')

    s = re.sub('\W', '', s)
    s = s.replace('_', ' ')
    s = re.sub('\s+', ' ', s)
    s = s.strip()
    s = s.replace(' ', '-')

    return s

def validate_ticket(s):
	global custom_url
	try:
		return int(s)
	except ValueError:
		pass


	url = "%s/tasks/" % custom_url
	if s.find(url) == 0:
		return int(re.match("\d*", s[len(url):]).group())

def reconfigure(config_filename):

	print """Company: Your Teamwork URL will be company.teamwork.com. 
If you have a custom domain, company.teamwork.com will redirect to it
but you'll have to find out what the value of company is. """
	company = raw_input("Company Name: ")

	print """Teamwork URL: What URL do you access Teamwork on?"""
	custom_url = raw_input("Company Name: [http://%s.teamwork.com]" % company)

	if not custom_url:
		custom_url = 'http://%s.teamwork.com' % company

	print """Your personal API key. To find this:
> Click on your avatar on any teamwork page, 
> Edit My Details
> API & Mobile
> Show your Token
> The value that appears goes here:"""
	key = raw_input("API Key: ")


	config = ConfigParser.ConfigParser()
	config.add_section('teamwork')
	config.set('teamwork', 'company', company)
	config.set('teamwork', 'apikey', key)
	config.set('teamwork', 'url', custom_url)
	with open(config_filename, 'wb') as configfile:
	    config.write(configfile)

	print " "
	print "Thanks, Saved that as %s. " % config_filename
	print "If you want to go though set again, run this with --reconfigure"

	return config
	
######## Config Creation

config_filename = expanduser("~/.teamworkrc")
config = ConfigParser.ConfigParser()
config.read(config_filename)

try:
	company = config.get('teamwork', 'company')
	key = config.get('teamwork', 'apikey')
	custom_url = config.get('teamwork', 'url')

except ConfigParser.Error as e:
	config = reconfigure(config_filename)

	company = config.get('teamwork', 'company')
	key = config.get('teamwork', 'apikey')
	custom_url = config.get('teamwork', 'url')


######## Parse Arguments

parser = argparse.ArgumentParser(description="Checkout a ticket branch")

parser.add_argument('ticket', metavar='task id (or url)', type=validate_ticket,
                   help='Ticket ID, either as an number or a teamwork url (eg %s/tasks/[TASKID])' % custom_url)

parser.add_argument('--hotfix', dest='hotfix', action='store_true',
                   help='If creating a branch, do it as a hotfix (default is Feature)')

parser.add_argument('--reconfigure', action='store_true',
                   help='Setup teamwork configuration')


args = parser.parse_args()

if args.reconfigure:
	config = reconfigure(config_filename)

	company = config.get('teamwork', 'company')
	key = config.get('teamwork', 'apikey')
	custom_url = config.get('teamwork', 'url')

	args = parser.parse_args()

taskid = args.ticket

NOTFOUND = -1

#########  Look up on Teamwork

if not taskid:
	print "Task ID not valid"
	sys.exit(5)

action = "tasks/%s.json" % taskid

request = urllib2.Request("https://{0}.teamwork.com/{1}".format(company, action))
request.add_header("Authorization", "BASIC " + base64.b64encode(key + ":xxx"))

response = urllib2.urlopen(request)
task = json.loads(response.read())['todo-item']

title = task['content']

# pprint(task)

print "[%s] %s " % (task['project-name'], task['todo-list-name'])
print title
print "*" * len(title)
print task['description']
print "---"
print "Created by %s %s" % (task['creator-firstname'], task['creator-lastname'])
if 'responsible-party-summary' in task:
	print "Assigned to %s " % (task['responsible-party-summary'])
else:
	print "Assigned to nobody yet"
if task['estimated-minutes']:
	print "Time estimate: %2.1fhrs" % (task['estimated-minutes']/60)
print "---"

#########  Check out the branch

try:
	repo = Repo(r".")
	git = repo.git
except git.exc.InvalidGitRepositoryError:
	print "This isn't a repository!"
	exit(5)

found = False
for branch in repo.heads:
	if branch.name.find(str(taskid)) != NOTFOUND:
		git.checkout(branch)
		print "Checking out local branch %s" % branch.name
		found = True
		break

if not found:
	remote_branches = repo.remote().fetch()
	for branch in remote_branches:
		if branch.name.find(str(taskid)) != NOTFOUND:
			git.checkout(branch, b=branch.name[7:])
			print "Checking out remote branch %s" % branch.name
			found = True
			break

if not found:
	####

	if args.hotfix:
		prefix = "hotfix"
	else:
		prefix = "feature"

	branch = "%s/%s-%s" % (prefix, taskid, slugify(title))

	g = Git()
	g.branch(branch, "master")
	g.checkout(branch)
	print "Created new branch %s" % branch

print "---"
