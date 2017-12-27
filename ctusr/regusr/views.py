import os
import getpass
import socket
import re
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.template import Template, Context
from django.conf import settings
from .forms import UploadForm
from datetime import date, datetime, timedelta
import urllib.parse

# required: django-crispy-forms

def index(request):
    if request.method == 'GET' and request.GET.get('next') == 'cleanup':
        response = HttpResponseRedirect(reverse('register'))
        response.delete_cookie(key='user', path='/')
        return response

    if request.COOKIES.get('user'):
        return go_to_registered()
    context_dict = dict()
    if request.method == 'POST':
        form = UploadForm(request.POST)
        if form.is_valid():
            (login, pw, descr) = register(form.cleaned_data['name'],
                                          get_client_id(request),
                                          form.cleaned_data['description'])
            return go_to_registered(login, pw, descr)
    else:
        form = UploadForm()
    context_dict['form'] = form
    return render(request, 'regusr/index.html', context=context_dict)


def go_to_registered(*args):
    response = HttpResponseRedirect(reverse('registered'))
    if args:
        (login, pw, description) = args
        expires = date.today() + timedelta(days=settings.USER_LIFETIME_DAYS)
        cookie = urllib.parse.urlencode({
            'login': login,
            'pw': pw,
            'description': description,
            'expires': expires.strftime("%Y-%m-%d") })
        response.set_cookie(key='user', value=cookie, path='/')
    return response


def split_lines(txt):
    return re.split('\r\n|\n|\r', txt)


def readlines(sock, recv_buffer=4096, delim='\n'):
    buffer = ''
    data = True
    while data:
        data = sock.recv(recv_buffer)
        buffer += data.decode()
        while buffer.find(delim) != -1:
            line, buffer = re.split('\r\n|\n|\r', buffer, 1)
            yield line
    return


def get_client_id(request):
    if 'HTTP_X_FORWARDED_FOR' in request.META:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        client_id = x_forwarded_for.split(',')[0]
    else:
        client_id = request.META.get('REMOTE_ADDR')
    if request.META.get('REMOTE_HOST'):
        client_id = client_id + ' / ' + request.META.get('REMOTE_HOST')
    return client_id


def register(upload_id, client, description):
    if isinstance(settings.USER_MANAGER_ADDRESS, str):
        socket_family = socket.AF_UNIX
    else:
        socket_family = socket.AF_INET
    sock = socket.socket(socket_family, socket.SOCK_STREAM)
    sock.connect(settings.USER_MANAGER_ADDRESS)
    sock.send(('upload_id:' + upload_id + '\n').encode('utf-8'))
    sock.send(('client:' + client + '\n').encode('utf-8'))
    for l in split_lines(description):
        sock.send(('description:' + l + '\n').encode('utf-8'))
    sock.send(b'end\n')
    resp = []
    for l in readlines(sock):
        resp.append(l)
        if len(resp) == 2:
            break
    sock.close()

    return (*resp, description)


def registered(request):
    request.session
    if not request.COOKIES.get('user'):
        return redirect(reverse('register'))
    data = dict(urllib.parse.parse_qsl(request.COOKIES['user']))
    context_dict = {
        'login': data['login'],
        'pw': data['pw'],
        'description': split_lines(data['description']),
        'expires': datetime.strptime(data['expires'], "%Y-%m-%d"),
        'server_ip': socket.gethostbyname(socket.gethostname())
    }
    return render(request, 'regusr/registered.html', context=context_dict)
