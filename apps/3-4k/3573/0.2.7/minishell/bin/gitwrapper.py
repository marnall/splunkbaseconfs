#!/usr/bin/python -u
#
# dulwich - Simple command-line interface to Dulwich
# Copyright (C) 2008-2011 Jelmer Vernooij <jelmer@samba.org>
# vim: expandtab
#
# Dulwich is dual-licensed under the Apache License, Version 2.0 and the GNU
# General Public License as public by the Free Software Foundation; version 2.0
# or (at your option) any later version. You can redistribute it and/or
# modify it under the terms of either of these two licenses.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# You should have received a copy of the licenses; if not, see
# <http://www.gnu.org/licenses/> for a copy of the GNU General Public License
# and <http://www.apache.org/licenses/LICENSE-2.0> for a copy of the Apache
# License, Version 2.0.
#

"""Simple command-line interface to Dulwich>

This is a very simple command-line wrapper for Dulwich. It is by
no means intended to be a full-blown Git command-line interface but just
a way to test Dulwich.
"""
from __future__ import print_function
import os
import sys
from getopt import getopt
import optparse
import signal
import logging

#def signal_int(signal, frame):
#    sys.exit(1)
#signal.signal(signal.SIGINT, signal_int)

from dulwich import porcelain
from dulwich.client import get_transport_and_path
from dulwich.errors import ApplyDeltaError
from dulwich.index import Index
from dulwich.pack import Pack, sha_to_hex
from dulwich.patch import write_tree_diff
from dulwich.repo import Repo
from io import open

def setup_logger(level):
    logger = logging.getLogger('minishell')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(os.path.join(os.environ.get("SPLUNK_HOME"), 'var', 'log', 'splunk', 'minishell.log'), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

logger = setup_logger(logging.INFO)

class Command(object):
    """A Dulwich subcommand."""

    def run(self, args):
        """Run the command."""
        raise NotImplementedError(self.run)


class cmd_archive(Command):

    def run(self, args):
        opts, args = getopt(args, "", [])
        client, path = get_transport_and_path(args.pop(0))
        location = args.pop(0)
        committish = args.pop(0)
        porcelain.archive(location, committish, outstream=sys.stdout,
            errstream=sys.stderr)


class cmd_add(Command):

    def run(self, args):
        opts, args = getopt(args, "", [])
        # workarround for false detenction of default encoding
        reload(sys)  # Reload does the trick!
        sys.setdefaultencoding('UTF8')

        porcelain.add(".", paths=args)


class cmd_rm(Command):

    def run(self, args):
        opts, args = getopt(args, "", [])

        porcelain.rm(".", paths=args)


class cmd_fetch_pack(Command):

    def run(self, args):
        opts, args = getopt(args, "", ["all"])
        opts = dict(opts)
        client, path = get_transport_and_path(args.pop(0))
        r = Repo(".")
        if "--all" in opts:
            determine_wants = r.object_store.determine_wants_all
        else:
            determine_wants = lambda x: [y for y in args if not y in r.object_store]
        client.fetch(path, r, determine_wants)


class cmd_fetch(Command):

    def run(self, args):
        opts, args = getopt(args, "", [])
        opts = dict(opts)
        client, path = get_transport_and_path(args.pop(0))
        r = Repo(".")
        if "--all" in opts:
            determine_wants = r.object_store.determine_wants_all
        refs = client.fetch(path, r, progress=sys.stdout.write)
        print("Remote refs:")
        for item in list(refs.items()):
            print("%s -> %s" % item)


class cmd_log(Command):

    def run(self, args):
        parser = optparse.OptionParser()
        parser.add_option("--reverse", dest="reverse", action="store_true",
                          help="Reverse order in which entries are printed")
        parser.add_option("--name-status", dest="name_status", action="store_true",
                          help="Print name/status for each changed file")
        options, args = parser.parse_args(args)

        porcelain.log(".", paths=args, reverse=options.reverse,
                      name_status=options.name_status,
                      outstream=sys.stdout)


class cmd_diff(Command):

    def run(self, args):
        opts, args = getopt(args, "", [])

        if args == []:
            print("Usage: dulwich diff COMMITID")
            sys.exit(1)

        r = Repo(".")
        commit_id = args[0]
        commit = r[commit_id]
        parent_commit = r[commit.parents[0]]
        write_tree_diff(sys.stdout, r.object_store, parent_commit.tree, commit.tree)


class cmd_dump_pack(Command):

    def run(self, args):
        opts, args = getopt(args, "", [])

        if args == []:
            print("Usage: dulwich dump-pack FILENAME")
            sys.exit(1)

        basename, _ = os.path.splitext(args[0])
        x = Pack(basename)
        print("Object names checksum: %s" % x.name())
        print("Checksum: %s" % sha_to_hex(x.get_stored_checksum()))
        if not x.check():
            print("CHECKSUM DOES NOT MATCH")
        print("Length: %d" % len(x))
        for name in x:
            try:
                print("\t%s" % x[name])
            except KeyError as k:
                print("\t%s: Unable to resolve base %s" % (name, k))
            except ApplyDeltaError as e:
                print("\t%s: Unable to apply delta: %r" % (name, e))


class cmd_dump_index(Command):

    def run(self, args):
        opts, args = getopt(args, "", [])

        if args == []:
            print("Usage: dulwich dump-index FILENAME")
            sys.exit(1)

        filename = args[0]
        idx = Index(filename)

        for o in idx:
            print((o, idx[o]))


class cmd_init(Command):

    def run(self, args):
        opts, args = getopt(args, "", ["bare"])
        opts = dict(opts)

        if args == []:
            path = os.getcwd()
        else:
            path = args[0]

        porcelain.init(path, bare=("--bare" in opts))
        """
        we apply some lovin' for splunk reasons
        """
        with open("."+'/.gitignore', 'w') as f:
            f.write('local/\n')
            f.write('*.sw?\n')
            f.close


class cmd_clone(Command):

    def run(self, args):
        opts, args = getopt(args, "", ["bare"])
        opts = dict(opts)

        if args == []:
            print("usage: dulwich clone host:path [PATH]")
            sys.exit(1)

        source = args.pop(0)
        if len(args) > 0:
            target = args.pop(0)
        else:
            target = None

        porcelain.clone(source, target, bare=("--bare" in opts))


class cmd_commit(Command):

    def run(self, args):
        opts, args = getopt(args, "", ["message"])
        print (opts)
        print (args)
        opts = dict(opts)
        #porcelain.commit(".", message=opts["--message"])
        message_bytes = b""
        message_bytes = str(opts)
        author = b""
        #author = realname+" <"+email+">"
        import cherrypy
        author = cherrypy.session['user']['fullName']+" "+cherrypy.session['user']['fullName']
        committer = b""
        committer = author
        commit = porcelain.commit(".", author=author, committer=committer, message=message_bytes)
        print (commit)


class cmd_commit_tree(Command):

    def run(self, args):
        opts, args = getopt(args, "", ["message"])
        if args == []:
            print("usage: dulwich commit-tree tree")
            sys.exit(1)
        opts = dict(opts)
        porcelain.commit_tree(".", tree=args[0], message=opts["--message"])


class cmd_update_server_info(Command):

    def run(self, args):
        porcelain.update_server_info(".")


class cmd_symbolic_ref(Command):

    def run(self, args):
        opts, args = getopt(args, "", ["ref-name", "force"])
        if not args:
            print("Usage: dulwich symbolic-ref REF_NAME [--force]")
            sys.exit(1)

        ref_name = args.pop(0)
        porcelain.symbolic_ref(".", ref_name=ref_name, force='--force' in args)


class cmd_show(Command):

    def run(self, args):
        opts, args = getopt(args, "", [])
        porcelain.show(".", args)


class cmd_diff_tree(Command):

    def run(self, args):
        opts, args = getopt(args, "", [])
        if len(args) < 2:
            print("Usage: dulwich diff-tree OLD-TREE NEW-TREE")
            sys.exit(1)
        porcelain.diff_tree(".", args[0], args[1])


class cmd_rev_list(Command):

    def run(self, args):
        opts, args = getopt(args, "", [])
        if len(args) < 1:
            print('Usage: dulwich rev-list COMMITID...')
            sys.exit(1)
        porcelain.rev_list(".", args)


class cmd_tag(Command):

    def run(self, args):
        opts, args = getopt(args, '', [])
        if len(args) < 2:
            print('Usage: dulwich tag NAME')
            sys.exit(1)
        porcelain.tag(".", args[0])


class cmd_repack(Command):

    def run(self, args):
        opts, args = getopt(args, "", [])
        opts = dict(opts)
        porcelain.repack(".")


class cmd_reset(Command):

    def run(self, args):
        opts, args = getopt(args, "", ["hard", "soft", "mixed"])
        opts = dict(opts)
        mode = ""
        if "--hard" in opts:
            mode = "hard"
        elif "--soft" in opts:
            mode = "soft"
        elif "--mixed" in opts:
            mode = "mixed"
        porcelain.reset(".", mode=mode, *args)


class cmd_daemon(Command):

    def run(self, args):
        from dulwich import log_utils
        from dulwich.protocol import TCP_GIT_PORT
        parser = optparse.OptionParser()
        parser.add_option("-l", "--listen_address", dest="listen_address",
                          default="localhost",
                          help="Binding IP address.")
        parser.add_option("-p", "--port", dest="port", type=int,
                          default=TCP_GIT_PORT,
                          help="Binding TCP port.")
        options, args = parser.parse_args(args)

        log_utils.default_logging_config()
        if len(args) >= 1:
            gitdir = args[0]
        else:
            gitdir = "."
        from dulwich import porcelain
        porcelain.daemon(gitdir, address=options.listen_address,
                         port=options.port)


class cmd_web_daemon(Command):

    def run(self, args):
        from dulwich import log_utils
        parser = optparse.OptionParser()
        parser.add_option("-l", "--listen_address", dest="listen_address",
                          default="",
                          help="Binding IP address.")
        parser.add_option("-p", "--port", dest="port", type=int,
                          default=8000,
                          help="Binding TCP port.")
        options, args = parser.parse_args(args)

        log_utils.default_logging_config()
        if len(args) >= 1:
            gitdir = args[0]
        else:
            gitdir = "."
        from dulwich import porcelain
        porcelain.web_daemon(gitdir, address=options.listen_address,
                             port=options.port)


class cmd_receive_pack(Command):

    def run(self, args):
        parser = optparse.OptionParser()
        options, args = parser.parse_args(args)
        if len(args) >= 1:
            gitdir = args[0]
        else:
            gitdir = "."
        porcelain.receive_pack(gitdir)


class cmd_upload_pack(Command):

    def run(self, args):
        parser = optparse.OptionParser()
        options, args = parser.parse_args(args)
        if len(args) >= 1:
            gitdir = args[0]
        else:
            gitdir = "."
        porcelain.upload_pack(gitdir)


class cmd_status(Command):

    def run(self, args):
        parser = optparse.OptionParser()
        options, args = parser.parse_args(args)
        if len(args) >= 1:
            gitdir = args[0]
        else:
            gitdir = "."
        status = porcelain.status(gitdir)
        if any(names for (kind, names) in list(status.staged.items())):
            sys.stdout.write("Changes to be committed:\n\n")
            for kind, names in list(status.staged.items()):
                for name in names:
                    sys.stdout.write("\t%s: %s\n" % (
                        kind, name.decode(sys.getfilesystemencoding())))
            sys.stdout.write("\n")
        if status.unstaged:
            sys.stdout.write("Changes not staged for commit:\n\n")
            for name in status.unstaged:
                sys.stdout.write("\t%s\n" %
                        name.decode(sys.getfilesystemencoding()))
            sys.stdout.write("\n")
        if status.untracked:
            sys.stdout.write("Untracked files:\n\n")
            for name in status.untracked:
                sys.stdout.write("\t%s\n" % name)
            sys.stdout.write("\n")


class cmd_ls_remote(Command):

    def run(self, args):
        opts, args = getopt(args, '', [])
        if len(args) < 1:
            print('Usage: dulwich ls-remote URL')
            sys.exit(1)
        refs = porcelain.ls_remote(args[0])
        for ref in sorted(refs):
            sys.stdout.write("%s\t%s\n" % (ref, refs[ref]))


class cmd_ls_tree(Command):

    def run(self, args):
        parser = optparse.OptionParser()
        parser.add_option("-r", "--recursive", action="store_true",
                          help="Recusively list tree contents.")
        parser.add_option("--name-only", action="store_true",
                          help="Only display name.")
        options, args = parser.parse_args(args)
        try:
            treeish = args.pop(0)
        except IndexError:
            treeish = None
        porcelain.ls_tree(
            ".", treeish, outstream=sys.stdout, recursive=options.recursive,
            name_only=options.name_only)


class cmd_pack_objects(Command):

    def run(self, args):
        opts, args = getopt(args, '', ['stdout'])
        opts = dict(opts)
        if len(args) < 1 and not '--stdout' in args:
            print('Usage: dulwich pack-objects basename')
            sys.exit(1)
        object_ids = [l.strip() for l in sys.stdin.readlines()]
        basename = args[0]
        if '--stdout' in opts:
            packf = getattr(sys.stdout, 'buffer', sys.stdout)
            idxf = None
            close = []
        else:
            packf = open(basename + '.pack', 'w')
            idxf = open(basename + '.idx', 'w')
            close = [packf, idxf]
        porcelain.pack_objects(".", object_ids, packf, idxf)
        for f in close:
            f.close()


class cmd_pull(Command):

    def run(self, args):
        parser = optparse.OptionParser()
        options, args = parser.parse_args(args)
        """
        try:
            from_location = args[0]
        except IndexError:
            from_location = None
        """
        from_location = args[0]
        try:
            repo = Repo(".")
            config = repo.get_config()
            remote = config.get(("remote", from_location), "url")
            print(to_location, file=sys.stderr)
            print(type(to_location), file=sys.stderr)
        except:
            print("we don't take a config from the .git/config but rather the passed string", file=sys.stderr)
            remote = from_location
            pass #we just keep to_location
        refspecs = args[1:] #usualy master
        porcelain.pull(".", remote, refspecs)

class cmd_push(Command):

    def run(self, args):
        import socket #set shorter timeout while testing
        socket.setdefaulttimeout(15)
        
        parser = optparse.OptionParser()
        options, args = parser.parse_args(args)
        if len(args) < 2:
            print("Usage: dulwich push TO-LOCATION REFSPEC..")
            sys.exit(1)
        to_location = args[0]
        try:
            repo = Repo(".")
            config = repo.get_config()
            remote = config.get(("remote", to_location), "url")
            print(to_location, file=sys.stderr)
        except:
            print("we don't take a config from the .git/config but rather the passed string", file=sys.stderr)
            remote = to_location
            pass #we just keep to_location
        refspecs = args[1:] #usualy master
        porcelain.push(".", remote, refspecs)
        print("pushed")

class cmd_remote_add(Command):

    def run(self, args):
        parser = optparse.OptionParser()
        options, args = parser.parse_args(args)
        porcelain.remote_add(".", args[0], args[1])


class cmd_remote(Command):

    subcommands = {
        "add": cmd_remote_add,
    }

    def run(self, args):
        if not args:
            print("Supported subcommands: %s" % ', '.join(list(self.subcommands.keys())))
            return False
        cmd = args[0]
        try:
            cmd_kls = self.subcommands[cmd]
        except KeyError:
            print('No such subcommand: %s' % args[0])
            return False
        return cmd_kls(args[1:])


class cmd_check_ignore(Command):

    def run(self, args):
        parser = optparse.OptionParser()
        options, args = parser.parse_args(args)
        ret = 1
        for path in porcelain.check_ignore(".", args):
            print(path)
            ret = 0
        return ret


class cmd_help(Command):

    def run(self, args):
        parser = optparse.OptionParser()
        parser.add_option("-a", "--all", dest="all",
                          action="store_true",
                          help="List all commands.")
        options, args = parser.parse_args(args)

        if options.all:
            print('Available commands:')
            for cmd in sorted(commands):
                print('  %s' % cmd)
        else:
            print("""\
help
The dulwich command line tool is currently a very basic frontend for the
Dulwich python module. For full functionality please see the API reference.
For a list of supported commands see 'dulwich help -a'.
""")


commands = {
    "add": cmd_add,
    "archive": cmd_archive,
    "check-ignore": cmd_check_ignore,
    "clone": cmd_clone,
    "commit": cmd_commit,
    "commit-tree": cmd_commit_tree,
    "daemon": cmd_daemon,
    "diff": cmd_diff,
    "diff-tree": cmd_diff_tree,
    "dump-pack": cmd_dump_pack,
    "dump-index": cmd_dump_index,
    "fetch-pack": cmd_fetch_pack,
    "fetch": cmd_fetch,
    "help": cmd_help,
    "init": cmd_init,
    "log": cmd_log,
    "ls-remote": cmd_ls_remote,
    "ls-tree": cmd_ls_tree,
    "pack-objects": cmd_pack_objects,
    "pull": cmd_pull,
    "push": cmd_push,
    "receive-pack": cmd_receive_pack,
    "remote": cmd_remote,
    "repack": cmd_repack,
    "reset": cmd_reset,
    "rev-list": cmd_rev_list,
    "rm": cmd_rm,
    "show": cmd_show,
    "status": cmd_status,
    "symbolic-ref": cmd_symbolic_ref,
    "tag": cmd_tag,
    "update-server-info": cmd_update_server_info,
    "upload-pack": cmd_upload_pack,
    "web-daemon": cmd_web_daemon,
    }

def git_command(args, path, splunk_realname, splunk_email):
    """
    print(sys.argv)
    if len(sys.argv) < 2:
        print("Usage: %s <%s> [OPTIONS...]" % (sys.argv[0], "|".join(commands.keys())))
        sys.exit(1)

    cmd = sys.argv[1]
    """
    import sys
    # workarround for false detenction of default encoding
    reload(sys)  # Reload does the trick!
    sys.setdefaultencoding('UTF8')
    
    #"." = args[0] # we pass current working dir from terminal.py
    global repoPath
    repoPath = "." #path
    logger.info("repoPath="+repoPath)
    
    global realname
    realname=splunk_realname
    global email
    email=splunk_email
    
    print("args: " + str(args))
    logger.info("args: "+args)    
    cmd = args[1]
    logger.info("cmd: "+cmd)
    try:
        """
        do socket handling, splunk might just have a empty proxy setting causing problems
        """
        import socket
        socket.setdefaulttimeout(15)
        import six.moves.urllib.request, six.moves.urllib.error, six.moves.urllib.parse
        urllib2.getproxies = lambda: {}
        import os
        import sys
        """
        #added for running it as a custom command, not needed here...
        import splunk.Intersplunk as si
        results, dummyresults, settings = si.getOrganizedResults()
        print >> sys.stderr, settings
        sessionKey = settings.get("sessionKey", None)
        authString = settings.get("authString", None)
        namespace = settings.get("namespace", None)
        REPOSITORY = namespace #no handling for repo parm yet
        scriptDir = sys.path[0]
        repoPath = os.path.abspath(os.path.join(scriptDir,'..','..',REPOSITORY))
        """
        
        cmd_kls = commands[cmd]
    except KeyError:
        print("No such subcommand: %s" % cmd)
        sys.exit(1)
    # TODO(jelmer): Return non-0 on errors
    cmd_kls().run(args[2:])
