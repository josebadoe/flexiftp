# FlexiFTP: Create and manage temporary Pure-FTPd users

This is a simple and quick solution for interchanging files over FTP, creating
temporary users with their passwords and with a relatively short lifetime,
that you can share with others for uploading and downloading stuff. You can
have multiple users that can't interfere with others, neither see their files.

[Pure-FTPd](https://www.pureftpd.org/project/pure-ftpd) was selected because
of it's ExtAuth feature that allows separating the user running the server
from the user managing the temporary users, and also allows for changes in the
userlist without the need to restart anything.

There are two main parts that take care of creating, authenticating, and later
removing temporary users, that may be created by anybody armed with the
correct URL (for now).

A [django 2.0](https://www.djangoproject.com/) application in the `ctusr`
directory for creating new users, and a local daemon in `usrmgr` to do the
dirty work.

The configuration settings for both are in `flexiftp/ctusr/ctusr/settings.py`.

## ctusr - the django application

This application just collects the necessary information and sends it to the
local daemon which responds with the created user's name and password, which
is then shown to the client.

### Configuration for Apache 2

The base directory of the web service is .../flexiftp/ctusr. So wherever you
install it, just replace <basedir> with the real path. And <wherever> is the
path where you want it to appear on your site (for example "/users").

If you want to change "/static" path, you'll have to change it also in
STATIC_URL in settings.py.


```
LoadModule wsgi_module modules/mod_wsgi.so

WSGIScriptAlias <wherever> <basedir>/ctusr/wsgi.py
WSGIPythonPath <basedir>

Alias /static "<basedir>/static"
<Directory <basedir>/static>
    Options -Indexes
    AllowOverride all
    Require all granted
</Directory>

<Directory <basedir>/ctusr>
    <Files wsgi.py>
        Require all granted
    </Files>
</Directory>
```


## usrmgr - the dirty doer

First, you need an executable. Here, the basedir is until the .../flexiftp. A
directory of the executables is called bindir, and you can place it wherever
you want, and it may be the same as the basedir. A temporary directory is also
used under the name tmp.

```
cd <basedir>/usrmgr
zip -9r <tmp>/usrmgr.zip .

cat <(echo "#!/usr/bin/env python") <tmp>/usrmgr.zip ><bindir>/usrmgr
rm <tmp>/usrmgr.zip
chmod +x <bindir>/usrmgr

cd <bindir>
ln -s usrmgr usrmgr-auth
ln -s usrmgr usrmgr-cleanup
ln -s usrmgr usrmgr-listener
```

And a simple script for running this with the correct options.

```
#!/bin/bash

BASE=<basedir>
cmd=$(basename $0)

$BASE/$cmd -s $BASE/flexiftp
```

And the a command like above:

```
cd <scriptdir>
ln -s <thescript> usrmgr-auth
```


## Systemd setup

Create some new services in `/etc/systemd/system`. If you have some other init
system, I hope you can understand and translate to your needs the contents of
these files.

### flexiftp-usrmgr.service

```
[Unit]
Description=FlexiFTP User Manager
After=network.target

[Service]
User=<your-chosen-ftp-user>
Group=<your-chosen-ftp-group>
Type=simple
ExecStart=<bindir>/usrmgr-listener -s <basedir>

[Install]
WantedBy=multi-user.target
```

For this you'll need a user and its group existing in your system, with
read/write access to a directory (USER_BASE_DIR in settings.py) where you
decided to keep the directories to create for every temporary user, and also
read/write access to a user database (USER_DB in settings.py), that you can
keep wherever you want it to. The chosen user may be a real account that you
can use for monitoring purposes.

This service will listen on the address specified in USEER_MANAGER_ADDRESS in
settings.py.


### pure-authd.service

```
[Unit]
Description=Pure-Authd server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/pure-authd -s /var/run/ftpd.sock -r <scriptdir>/usrmgr-auth

[Install]
WantedBy=multi-user.target
```

## Pure-FTPd setup

Here we have only a few but important settings:

```
# avoid the temporary users seeing anything else
ChrootEveryone yes

# this must be the same as the argument of pure-authd
ExtAuth /var/run/ftpd.sock

# this should be less or equal to the UID of <your-chosen-ftp-user>,
# with which you run the usrmgr-listener.
MinUID 1234
```


## Senicide - killing off the old ones

With your chosen ftp user, add something like this to your crontab, to run at
least once a day in some lonely hour. This find the users whose creation time
is before today minus USER_LIFETIME_DAYS (in settings.py) and remove them from
the database and their directory from USER_BASE_DIR.

```
M H * * * <bindir>/usrmgr-cleanup -s <basedir>
```
