import splunk.Intersplunk as si
import splunk
import splunk.rest as rest
"""
do socket handling, splunk might just have a empty proxy setting causing problems
"""
import socket
socket.setdefaulttimeout(15)
import urllib2
urllib2.getproxies = lambda: {}
import os
import sys
import re
import os
import tempfile
import json
import splunklib.client as client
import traceback
import collections
from datetime import datetime,timedelta
import jsonpickle
import socket
socket.setdefaulttimeout(15)

def print_filecontents(f, rowname):
    results = []
    result = {}
    #help_file = open(path,"r")
    f.seek(0, 0)
    content = f.readlines()
    print >> sys.stderr, content
    result[rowname] = content
    results.append(result)
    splunk.Intersplunk.outputResults(results)

def parseCommit(commitLines): # heavily borrowed from https://github.com/johnkchiu/GitLogParser/blob/master/gitLogParser.py
        """
        try to format the log into a table for splunk
        um, somehow i loose tha last ( i.e. oldest) commit on the way
        """
	# dict to store commit data
	commit = collections.OrderedDict() #{}
	# iterate lines and save
	for nextLine in commitLines:
                print >> sys.stderr, nextLine
		if nextLine == '' or nextLine == '\n':
			# ignore empty lines
			pass
		elif bool(re.match('commit:', nextLine, re.IGNORECASE)):
			# commit xxxx
                        print >> sys.stderr, "a new commit! woohoo - line read like so - " + nextLine
			if len(commit) != 0:		## new commit, so re-initialize
				commits.append(commit)
				commit = {}
			commit = {'commit' : re.match('commit: (.*)', nextLine, re.IGNORECASE).group(1) }
		elif bool(re.match('merge:', nextLine, re.IGNORECASE)):
			# Merge: xxxx xxxx
			pass
		elif bool(re.match('author:', nextLine, re.IGNORECASE)):
			# Author: xxxx <xxxx@xxxx.com>
			m = re.compile('Author: (.*) <(.*)>').match(nextLine)
			commit['author'] = m.group(1)
			commit['email'] = m.group(2)
                elif bool(re.match('Committer:', nextLine, re.IGNORECASE)):
                        # Date: xxx
                        m = re.compile('Committer: (.*)').match(nextLine)
                        commit['commiter'] = m.group(1)
		elif bool(re.match('Date:', nextLine, re.IGNORECASE)):
			# Date: xxx
                        m = re.compile('Date: (.*)').match(nextLine)
                        commit['date'] = m.group(1)
                        timedate_notimezone = m.group(1)[0:-6]
                        epoch = datetime.strptime(timedate_notimezone, " %a %b %d %Y %H:%M:%S") # hack, no %z in python 2.7
                        timedate_timezoneoffset = m.group(1)[-5:]
                        if timedate_timezoneoffset[0:1] == "+":
                            epoch-=timedelta(hours=int(timedate_timezoneoffset[2:3]),minutes=int(timedate_timezoneoffset[4:5]))
                        elif timedate_timezoneoffset[0:1] == '-':
                            epoch+=timedelta(hours=int(timedate_timezoneoffset[2:3]),minutes=int(timedate_timezoneoffset[4:5]))
                        commit["_time"] = epoch 
		elif bool(re.match('    ', nextLine, re.IGNORECASE)):
			# (4 empty spaces)
			if commit.get('message') is None:
				commit['message'] = nextLine.strip()
                elif nextLine == "--------------------------------------------------\n":
                        pass
		else:
                        #print ('ERROR: Unexpected Line: ' + nextLine)
                        #pass

                        if commit.get('message') is None:
                                commit['message'] = nextLine.strip()


try:
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
    #app = options.get('app','..')
    command = sys.argv[1]
    REPOSITORY = options.get('repository','')
    REPOSITORY = options.get('app',REPOSITORY)
    paths = options.get('paths','')
    branch = options.get('branch','')
    message = options.get('message','no specific comments')
    source = options.get('source','')
    commit = options.get('commit','')
    remote = options.get('remote','')

    results, dummyresults, settings = si.getOrganizedResults()
    print >> sys.stderr, settings
    sessionKey = settings.get("sessionKey", None)
    authString = settings.get("authString", None)
    namespace = settings.get("namespace", None)
    if REPOSITORY == "":
        REPOSITORY = namespace #fallback to the app in wich we run
    print >> sys.stderr, "Repository to use: " + str(REPOSITORY)
    if authString != None:
        start = authString.find('<userId>') + 8
        stop = authString.find('</userId>')
        cn = authString[start:stop]
        serverResponse, serverContent = rest.simpleRequest('/services/authentication/users/'+cn, sessionKey=sessionKey)
        service = client.connect(token=sessionKey)
        #users = service.users
        for user in service.users:
            if user.name == cn:
                realname = user.realname
                email = user.email

except Exception, e:
    import traceback
    stack = traceback.format_exc()

from dulwich import porcelain

scriptDir = sys.path[0]
repoPath = os.path.abspath(os.path.join(scriptDir,'..','..',REPOSITORY))

print >> sys.stderr, "repo path: " + str(repoPath)

try: #try to run a command
    if command == "init":
        porcelain.init(repoPath)
        porcelain.show(repoPath)
        with open(repoPath+'/.gitignore', 'w') as f:
            f.write('local/\n')
            f.write('*.sw?\n')
            f.close
    elif command == "ls":
        print "x,type,hash,path"
        porcelain.ls_tree(repoPath)
        #orcelain.show('..')
    elif command == "add":
        if paths == '':
            porcelain.add(repoPath) # file(s) to add, defaults to app name
        else:
            porcelain.add(repoPath, paths)
        print "next steps:\nrun '|git status' to show what is ready to commit etc and '|git commit' to commit"
    elif command == "commit":
        """
        def commit(repo='.', message=None, author=None, committer=None):
        Create a new commit.
        Parameters	repo	Path to repository
        message	Optional commit message
        author	Optional author name and email
        committer	Optional committer name and email
        Returns	SHA1 of the new commit
        """
        author = b""
        author = realname+" <"+email+">"
        committer = b""
        committer = author
        message_bytes = b""
        message_bytes = message
        print >> sys.stderr, author
        print >> sys.stderr, message_bytes
        """
        try:
            commit = porcelain.commit(repo=repoPath, author=author, message=message_bytes)
            print >> sys.stderr, commit
            # the commit id is in the commit variable - try to print it nicely to give feedback
            porcelain.print_commit(commit)
            print "log"
            print message
            porcelain.log(repoPath)
        except:
            print >> sys.stderr, "trying to commit resulted in a failure"
            traceback.print_exc(file=sys.stderr)
            print "something went wrong"
        """
        commit = porcelain.commit(repo=repoPath, author=author, committer=committer, message=message_bytes)
        print >> sys.stderr, commit
        print "next steps:\nrun '|git log' to show the history"
        # the commit id is in the commit variable - try to print it nicely to give feedback
        #porcelain.print_commit(commit)
    elif command == "status":
        print >> sys.stderr, "status"
        status = porcelain.status(repoPath)
        # status(tracked_changes, unstaged_changes, untracked_changes)
        results = []
        result = collections.OrderedDict() # {
        result["add"]=status[0]["add"]
        result["modify"]=status[0]["modify"]
        result["delete"]=status[0]["delete"]
        result["unstaged_changes"]=status[1] #unstaged
        result["untracked_changes"]=status[2] #unstaged
        results.append(result)
        splunk.Intersplunk.outputResults(results)
        
    elif command == "treechanges":
        porcelain.get_tree_changes(repoPath)
    elif command == "branch":
        """
        def branch_list(repo):
        List all branches.
        Parameters	repo	Path to the repository
        """
        branches = porcelain.branch_list(repoPath)
        print "branches"
        for item in branches:
            print item
    elif command == "fetch":
        """
        def fetch(repo, remote_location, outstream=sys.stdout, errstream=default_bytes_err_stream):
        Fetch objects from a remote server.
        Parameters	repo	Path to the repository
        remote_location	String identifying a remote server
        outstream	Output stream (defaults to stdout)
        errstream	Error stream (defaults to stderr)
        Returns	Dictionary with refs on the remote
        """
        porcelain.fetch(repoPath,remote) # remote should be the host etc from a stanze
    elif command == "createbranch":
        """
        def branch_create(repo, name, objectish=None, force=False):
        Create a branch.
        Parameters	repo	Path to the repository
        name	Name of the new branch
        objectish	Target object to point new branch at (defaults to HEAD)
        force	Force creation of branch, even if it already exists   
        """
        porcelain.branch_create(repoPath,branch)
    elif command == "deletebranch":
        """
        def branch_delete(repo, name):
        Delete a branch.
        Parameters	repo	Path to the repository
        name	Name of the branch
        """
        porcelain.branch_delete(repoPath,branch)
    elif command == "printcommit":
        """
        def print_commit(commit, decode, outstream=sys.stdout):
        Write a human-readable commit log entry.
        Parameters	commit	A Commit object
        outstream	A stream file to write to
        """
        print >> sys.stderr, "handle command printcommit"
        print >> sys.stderr, commit
        decode = lambda x: commit_decode(entry.commit, x)
        porcelain.print_commit(commit, decode=decode)
    elif command == "diff-tree":
        """
        diff_tree(repo, old_tree, new_tree, outstream=sys.stdout):
        Compares the content and mode of blobs found via two tree objects.
        :param repo: Path to repository
        :param old_tree: Id of old tree
        :param new_tree: Id of new tree
        :param outstream: Stream to write to
        """
        print >> sys.stderr, "handle command diff-tree"
        print >> sys.stderr, "old tree: " + str(sys.argv[2])
        print >> sys.stderr, "new tree: " + str(sys.argv[3])
        porcelain.diff_tree(repoPath,sys.argv[2], sys.argv[3])
    elif command == "ls-tree":
        try:
            treeish=sys.argv[2]
        except IndexError:
            treeish='HEAD' # fallback to HEAD
        print treeish
        porcelain.ls_tree(repoPath, treeish)
    elif command == "fetch":
        """
        def fetch(repo, remote_location, outstream=sys.stdout, errstream=default_bytes_err_stream):
        """
        print >> sys.stderr, "handle command fetch"
        porcelain.fetch(repoPath,remote)
    elif command == "ls-remote":
        print >> sys.stderr, "handle command ls-remote"
        porcelain.ls_remote(remote)
    elif command == "remote":
        print >> sys.stderr, "handle command remote"
        try:
            verb = sys.argv[2]
            if verb == "add":
                """
                def remote_add(repo, name, url):
                Add a remote.
                :param repo: Path to the repository
                :param name: Remote name
                :param url: Remote URL
                """
                porcelain.remote_add(repoPath,sys.argv[3],sys.argv[4])

        except IndexError:
             print >> sys.stderr, "not sure what you want, consult help"
    elif command == "log":
        """
        def log(repo='.', paths=None, outstream=sys.stdout, max_entries=None, reverse=False, name_status=False):
        Write commit logs.
        Parameters	repo	Path to repository
        paths	Optional set of specific paths to print entries for
        outstream	Stream to write log output to
        reverse	Reverse order in which entries are printed
        name_status	Print name status
        max_entries	Optional maximum number of entries to display
        """
        print >> sys.stderr, "handle command log"
        #print "log"
        #porcelain.log(repoPath)       
	temp = tempfile.TemporaryFile(prefix='tmp_')
        print >> sys.stderr, temp.name
        porcelain.log(repoPath, outstream=temp)

        temp.seek(0, 0)
        content = temp.readlines()
        #print >> sys.stderr, content
        results = []
        commits = []
        parseCommit(content)
        splunk.Intersplunk.outputResults(commits)
        """
        for commit in commits:
            results.append(commit)
        results = []
        result = {}
        result["log"] = content
        results.append(result)
        splunk.Intersplunk.outputResults(results)

        #print_filecontents(temp, "log")
        """
        temp.close()
    elif command == "show":
        print >> sys.stderr, "handle command show"
        porcelain.show(repoPath)
    elif command == "config":
        print >> sys.stderr, "handle command config"
        from dulwich.repo import Repo
        repo = Repo(repoPath)
        config = repo.get_config()
        try:
            print(config.get("core", "filemode"))
            print >> sys.stderr, "core config filemode: " + str(config.get("core", "filemode"))
            print(config.get(("remote", "origin"), "url"))
        except:
            errorResults = splunk.Intersplunk.generateErrorResults( jsonpickle.encode(config.get("remote", "origin"))  )
            splunk.Intersplunk.outputResults(errorResults)
            pass
    elif command == "clone":
        """
        def clone(source, target=None, bare=False, checkout=None, errstream=default_bytes_err_stream, outstream=None, origin='origin'):
        Clone a local or remote git repository.
        Parameters	source	Path or URL for source repository
        target	Path to target repository (optional)
        bare	Whether or not to create a bare repository
        checkout	Whether or not to check-out HEAD after cloning
        errstream	Optional stream to write progress to
        outstream	Optional stream to write progress to (deprecated)
        returns	The new repository
        # example: porcelain.clone("git://github.com/jelmer/dulwich", "dulwich-clone")
        """
        print >> sys.stderr, "trying to clone a repository"
        porcelain.clone(source,name)
    elif command == "push":
        """
        def push(repo, remote_location, refspecs, outstream=default_bytes_out_stream, errstream=default_bytes_err_stream):
        Remote push with dulwich via dulwich.client
        Parameters	repo	Path to repository
        remote_location	Location of the remote
        refspecs	Refs to push to remote
        outstream	A stream file to write output
        errstream	A stream file to write errors
        # example: >>> tr = porcelain.init("targetrepo")
        #          >>> r = porcelain.push("testrepo", "targetrepo", "master")
        """
        from dulwich.repo import Repo
        repo = Repo(repoPath)
        config = repo.get_config()

        remote = config.get(("remote", "origin"), "url")
        print >> sys.stderr, "remote: " , remote
        #refs = repo.get_refs()
        print >> sys.stderr, "try to push " , repoPath + " to " + remote
        print >> sys.stderr, "local head: " + sys.argv[3]
        porcelain.push(repoPath, remote, sys.argv[3]) #used to be 'master' as hard coded default
        print "done i guess... next steps:\nrun '|git log' to show the history"

        # used to be , refs["refs/heads/master"]) but yeah branch seems to be whats asked of us...

    elif command == "pull":
        """
        def pull(repo, remote_location=None, refspecs=None, outstream=default_bytes_out_stream, errstream=default_bytes_err_stream):
        Pull from remote via dulwich.client
        Parameters	repo	Path to repository
        remote_location	Location of the remote
        refspec	refspecs to fetch
        outstream	A stream file to write to output
        errstream	A stream file to write to errors
        # probably like this r = porcelain.pull("localrepo","git://github.com/jelmer/dulwich","master")
        """
        print >> sys.stderr, "not yet implemented..."

    elif command == "help": # dump help.txt, i know - cheap right?
        file = open("help.txt","r")
        print_filecontents(file, "help")
        file.close()

except Exception, e:
    import traceback
    stack = traceback.format_exc()
    traceback.print_exc(file=sys.stderr)
    errorResults = splunk.Intersplunk.generateErrorResults(stack)
    splunk.Intersplunk.outputResults(errorResults)

