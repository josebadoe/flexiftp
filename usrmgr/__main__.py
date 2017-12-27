import os
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-s", metavar="DIR",
                    help="Server base directory",
                    dest="server_base", default=None)
parser.add_argument("-d", metavar="DB",
                    help="User DB file. If not present, its value is taken"
                    " from USER_DB in settings.py",
                    dest="db", default=None)
parser.add_argument("-l", metavar="AGE",
                    help="Registered users' life time in days. If not present, its "
                    " value is taken from USER_LIFETIME_DAYS in settings.py",
                    dest="lifetime", default=None)
name_parts = os.path.basename(sys.argv[0]).split('-',1)
if len(name_parts) != 2:
    parser.add_argument("command", metavar="CMD")
parser.add_argument("args", nargs="*")

# rsync -avz src/flexiftp bin/flexiftp/usrmgr -e ssh indra-rd@indra-vm:/usr/local/share/webapps/flexiftp/

args = parser.parse_args()
if not args.server_base:
    print("The -s option is obligatory. Use -h for help.")
    sys.exit(1)

sys.path.append(os.path.join(args.server_base, 'ctusr'))
import usrmgr
from ctusr import settings

if not args.db:
    args.db = settings.USER_DB
if not args.lifetime:
    args.lifetime = settings.USER_LIFETIME_DAYS

#     print("%r" % (usrmgr.Server(args.db).add_user('.  Johanna / Bob - Kertivosok!-! ', ['a', 'b', 'c']),))

if len(name_parts) == 2:
    cmd = name_parts[1]
else:
    cmd = args.command

server = usrmgr.Server(args.db)

if cmd == 'listener' and not args.args:
    server.listen()
elif cmd == 'auth' and len(args.args) in [2,0]:
    # variables set by pure-authd before call
    if len(args.args) == 2:
        login = args.args[0]
        pw = args.args[1]
    else:
        login = os.environ['AUTHD_ACCOUNT']
        pw = os.environ['AUTHD_PASSWORD']
    server.auth(login, pw)
elif cmd == 'add':
    for u in args.args:
        (login, pw) = server.create_login(u)
        print("%s: Login: %s, password: %s" % (u, login, pw))
elif cmd == 'cleanup':
    server.cleanup(int(args.lifetime))
else:
    parser.print_help()
    sys.exit(1)
