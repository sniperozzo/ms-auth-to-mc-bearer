import os
import re
import json

try:
    from urlparse import urlparse, parse_qs
    from urllib import urlencode, unquote
except ImportError:  # py 3.x
    from urllib.parse import urlparse, parse_qs, urlencode, unquote

import requests


# Literally Xbox's API Wrapper code changed just some requests, there is probably some stuff you don't need and can remove, the real version 
# I made of ms-auth-to-ms-bearer is written in C so forgive me if I left some dumb useless code below

class Client(object):

    def __init__(self):
        self.session = requests.session()
        self.authenticated = False

    def _raise_for_status(self, response):
        if response.status_code == 400:
            try:
                description = response.json()['description']
            except:
                description = 'Invalid request'
            raise KeyError(description)

    def _get(self, url, **kw):
        '''
        Makes a GET request, setting Authorization
        header by default
        '''
        headers = kw.pop('headers', {})
        headers.setdefault('Content-Type', 'application/json')
        headers.setdefault('Accept', 'application/json')
        headers.setdefault('Authorization', self.AUTHORIZATION_HEADER)
        kw['headers'] = headers
        resp = self.session.get(url, **kw)
        self._raise_for_status(resp)
        return resp

    def _post(self, url, **kw):
        '''
        Makes a POST request, setting Authorization
        header by default
        '''
        headers = kw.pop('headers', {})
        headers.setdefault('Authorization', self.AUTHORIZATION_HEADER)
        kw['headers'] = headers
        resp = self.session.post(url, **kw)
        self._raise_for_status(resp)
        return resp

    def _post_json(self, url, data, **kw):
        '''
        Makes a POST request, setting Authorization
        and Content-Type headers by default
        '''
        data = json.dumps(data)
        headers = kw.pop('headers', {})
        headers.setdefault('Content-Type', 'application/json')
        headers.setdefault('Accept', 'application/json')

        kw['headers'] = headers
        kw['data'] = data
        return self._post(url, **kw)

    def authenticate(self, login=None, password=None):
        '''
        Authenticated this client instance.

        ``login`` and ``password`` default to the environment
        variables ``MS_LOGIN`` and ``MS_PASSWD`` respectively.


        :param login: Email address associated with a microsoft account
        :param password: Matching password

        :raises: :class:`~xbox.exceptions.AuthenticationException`

        :returns: Instance of :class:`~xbox.Client`

        '''
        if login is None:
            login = os.environ.get('MS_LOGIN')

        if password is None:
            password = os.environ.get('MS_PASSWD')

        if not login or not password:
            msg = (
                'Authentication credentials required. Please refer to '
                'http://xbox.readthedocs.org/en/latest/authentication.html'
            )
            raise KeyError(msg)

        self.login = login

        # firstly we have to GET the login page and extract
        # certain data we need to include in our POST request.
        # sadly the data is locked away in some javascript code
        base_url = 'https://login.live.com/oauth20_authorize.srf?'

        # if the query string is percent-encoded the server
        # complains that client_id is missing
        qs = unquote(urlencode({
            'client_id': '0000000048093EE3',
            'redirect_uri': 'https://login.live.com/oauth20_desktop.srf',
            'response_type': 'token',
            'display': 'touch',
            'scope': 'service::user.auth.xboxlive.com::MBI_SSL',
            'locale': 'en',
        }))
        resp = self.session.get(base_url + qs)

        # python 3.x will error if this string is not a
        # bytes-like object
        url_re = b'urlPost:\\\'([A-Za-z0-9:\?_\-\.&/=]+)'
        ppft_re = b'sFTTag:\\\'.*value="(.*)"/>'

        login_post_url = re.search(url_re, resp.content).group(1)
        post_data = {
            'login': login,
            'passwd': password,
            'PPFT': re.search(ppft_re, resp.content).groups(1)[0],
            'PPSX': 'Passpor',
            'SI': 'Sign in',
            'type': '11',
            'NewUser': '1',
            'LoginOptions': '1',
            'i3': '36728',
            'm1': '768',
            'm2': '1184',
            'm3': '0',
            'i12': '1',
            'i17': '0',
            'i18': '__Login_Host|1',
        }

        resp = self.session.post(
            login_post_url, data=post_data, allow_redirects=False,
        )

        if 'Location' not in resp.headers:
            # we can only assume the login failed
            msg = 'Could not log in with supplied credentials'
            raise KeyError(msg)

        # the access token is included in fragment of the location header
        location = resp.headers['Location']
        parsed = urlparse(location)
        fragment = parse_qs(parsed.fragment)
        access_token = fragment['access_token'][0]

        url = 'https://user.auth.xboxlive.com/user/authenticate'
        resp = self.session.post(url, data=json.dumps({
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": access_token,
            }
        }), headers={'Content-Type': 'application/json'})

        json_data = resp.json()
        user_token = json_data['Token']
        self.auth_uhs = json_data['DisplayClaims']['xui'][0]['uhs']
        uhs = json_data['DisplayClaims']['xui'][0]['uhs']

        url = 'https://xsts.auth.xboxlive.com/xsts/authorize'
        resp = self.session.post(url, data=json.dumps({
            "RelyingParty": "rp://api.minecraftservices.com/",
            "TokenType": "JWT",
            "Properties": {
                "UserTokens": [user_token],
                "SandboxId": "RETAIL",
            }
        }), headers={'Content-Type': 'application/json'})

        response = resp.json()
        self.auth_xsts = response['Token']
        self.AUTHORIZATION_HEADER = 'XBL3.0 x=%s;%s' % (uhs, response['Token'])
        self.authenticated = True
        return self

    def __repr__(self):
        if self.authenticated:
            return '<xbox.Client: %s>' % self.login
        else:
            return '<xbox.Client: Unauthenticated>'


def gather_mc_bearer(email, passwd):
    oauth_client = Client()
    oauth_client.authenticate(login=email, password=passwd)
    # I prefer resp = and not with resp as when doing small requests so stfu :(
    resp = requests.post("https://api.minecraftservices.com/authentication/login_with_xbox",
                         headers={"Content-Type": "application/json", "Accept": "application/json"},
                         json={"identityToken": f"XBL3.0 x={oauth_client.auth_uhs};{oauth_client.auth_xsts}"})  # here I could use AUTHORIZATION_HEADER from Xbox's code but I this is better
    try:
        bearer = resp.json()['access_token']
        return bearer
    except KeyError:
        print("Well this is awkward, you should not be here as it is nearly impossible but if you are check if Minecraft's API is down.")
