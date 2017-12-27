#!/usr/bin/env python

import socket
import sys
import os
import atexit
import re
import sqlite3
import string, random
import shutil
from ctusr import settings

class Server:
    def __init__(self, dbfile):
        self.server_address = settings.USER_MANAGER_ADDRESS
        self.socket_family = socket.AF_INET
        self.sock = None
        self.db_conn = None
        self.dbfile = dbfile
        self.uid = os.getuid()
        self.gid = os.getgid()


    def listen(self):
        self.sock = socket.socket(self.socket_family, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        atexit.register(self.remove_socket)
        self.sock.bind(self.server_address)
        self.sock.listen(1)
        self.listener()


    def remove_socket(self):
        if self.sock:
            self.sock.close()
        if self.db_conn:
            self.db.close()

    tags = [ ('upload_id', False), ('description', True), ('client', False) ]

    def listener(self):
        print("waiting for a connection", file=sys.stderr)
        while True:
            (connection, client_address) = self.sock.accept()
            try:
                print("connection from %r" % (client_address,), file=sys.stderr)
                data = dict()
                for l in self.readlines(connection):
                    if l == 'end':
                        break
                    for (t, multiline) in self.tags:
                        if l.startswith(t + ':'):
                            v = l[len(t)+1:]
                            if multiline:
                                if t in data:
                                    data[t].append(v)
                                else:
                                    data[t] = [v]
                            else:
                                data[t] = v
                (login, pw) = self.add_user(**data)
                connection.send((login + '\n').encode('ascii'))
                connection.send((pw + '\n').encode('ascii'))
            finally:
                connection.close()


    def readlines(self, sock, recv_buffer=4096, delim='\n'):
        buffer = ''
        data = True
        while data:
            data = sock.recv(recv_buffer)
            buffer += data.decode()
            while buffer.find(delim) != -1:
                line, buffer = re.split('\r\n|\n|\r', buffer, 1)
                yield line
        return


    @property
    def db(self):
        if self.db_conn is None:
            new_db = not os.path.exists(self.dbfile)
            self.db_conn = sqlite3.connect(self.dbfile)
            if new_db:
                self.db_conn.execute("""
                create table users (
                  login text primary key,
                  password text not null,
                  client text,
                  created datetime not null,
                  uid int not null,
                  gid int not null
                )
                """)
                #settings.USER_DB)
        return self.db_conn


    login_min_length = 3
    login_max_length = 40


    def fix_up_username(self, upload_id):
        a = upload_id.lower().strip()
        b = str()
        for c in a:
            if c.isspace():
                if b and b[-1] not in '_-':
                    b += '_'
            elif c.isalnum():
                b += c
            else:
                if b and b[-1] == '_':
                    b = b[0:-1] + '-'
                elif b and b[-1] != '-':
                    b += '-'
        if len(b) > self.login_max_length:
            b = b[0:15]
        while len(b) < self.login_min_length:
            b += random.choice(string.ascii_lowercase)
        if b and b[-1] in '_-':
            b = b[0:-1]
        return b


    def genpw(self):
        pw_base = string.ascii_letters + string.digits
        l = random.randint(7, 12)
        p = random.randint(1, 6)
        pw = ''
        for i in range(0, l):
            if i == p:
                pw += random.choice(string.punctuation)
                p = random.randint(i+3, i+6)
            else:
                pw += random.choice(pw_base)
        return pw


    def create_login(self, upload_id, client):
        name = self.fix_up_username(upload_id)
        login = name
        seq = 0
        c = self.db.cursor()
        pw = self.genpw()

        while True:
            c.execute("select 1 from users where login = ?", (login,))
            if c.fetchone():
                seq += 1
                login = "%s-%d" % (name, seq)
            else:
                self.db.execute("insert into users values (?, ?, ?, datetime('now'), ?, ?)",
                                (login, pw, client, self.uid, self.gid))
                self.db.commit()
                c.close()
                return (login, pw)


    def user_dir(self, login):
        return os.path.join(settings.USER_BASE_DIR, login)


    def add_user(self, upload_id, description, client=None):
        (login, pw) = self.create_login(upload_id, client)
        user_dir = self.user_dir(login)
        os.mkdir(user_dir)
        if description:
            banner = os.path.join(user_dir, ".banner")
            with open(banner, 'w') as f:
                for l in description:
                    print(l, file=f)
        return (login, pw)


    def auth(self, login, pw):
        try:
            c = self.db.cursor()
            c.execute("select password, uid, gid from users where login = ?", (login,))
            row = c.fetchone()
            c.close()
            if row and row[0] == pw:
                (_, uid, gid) = row
                print("auth_ok:1")
                print("uid:%d" % uid)
                print("gid:%d" % gid)
                print("dir:%s" % self.user_dir(login))
                print("end")
                return True
            elif row:
                print("auth_ok:-1")
            else:
                print("auth_ok:0")
        except Exception:
            print("auth_ok:0")

        return False


    def cleanup(self, lifetime):
        """Delete users and their directories after reaching 'lifetime' time of
        age. The argument should specify lifetime as 'N days', months, or
        years. Plural and singular forms are both acceptable.
        """
        c = self.db.cursor()
        cur = c.execute("select login from users where created < date('now', ? || ' days')",
                        (-lifetime,))
        for (login,) in cur:
            d = self.user_dir(login)
            shutil.rmtree(d)
            self.db.execute("delete from users where login = ?", (login,))
            self.db.commit()
