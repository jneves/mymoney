# -*- coding: utf-8 -*-
import requests
import urllib.request
import urllib.parse
import urllib.error
import bs4
import time
import re
import logging

from datetime import datetime, date
from .bank import Bank
from .account import Account
from .transaction import Transaction


BASE_URL = "https://www.particulares.santandertotta.pt/"
LOGIN_PAGE = "bepp/sanpt/usuarios/login/?"
GETTRANSACTIONS_URL = BASE_URL + "/bepp/sanpt/cuentas/listadomovimientoscuenta/0,,,0.shtml"


class RedirectedException(Exception):
    pass


class AuthenticationException(Exception):
    pass


def post_request(url, values):
    data = urllib.parse.urlencode(values)
    req = urllib.request.Request(url, data)
    return urllib.request.urlopen(req)


class Santander(Bank):
    name = "Santander"
    __OSVSTATE = None
    __VIEWSTATE = None

    def login(self):
        self.start()
        self.authenticate(self.info["user"], self.info["pass"])

    def start(self, cookie_file=None):
        self.cookie_file = cookie_file
        # CURRENTLY NOT SUPPORTING SESSION REUSE
        self.load_session(False)

    def get_page(self, url, parameters=None, allow_redirects=False):
        if parameters:
            d = urllib.parse.urlencode(parameters)
            data = d.encode("utf8")
            f = self.opener.open(url, data)
        else:
            f = self.opener.open(url)
        
        if not allow_redirects and f.geturl() != url:
            raise RedirectedException("got "+f.geturl()+" instead of "+url)
        html = f.read()
        if True:
            with open("response.html", 'w') as fo:
                fo.write(html.decode('utf8'))
        return html

    def load_session(self, file_present=True):
        self.session = requests.Session()
        s = self.session
        r = s.get(
            BASE_URL,
            allow_redirects=True,
            verify=False,
        )

        # get next url
        soup = bs4.BeautifulSoup(r.text, 'html.parser')
        iframes = soup.find_all('iframe')
        url = BASE_URL + iframes[0].attrs['src']

        # get params
        r = s.get(
            url
        )
        self.login_params = {
        # These two seem fixed and seem not to make a difference
        #   'sessiontoken': '5abcfd042b26eb423ae0ebda84f8505',  
        #   'P2hoCyPjpg': 'bGFuZ3VhZ2U6ZW4tR0IsY29sb3JEZXB0aDoyNCxkZXZpY2VNZW1vcnk6bm90IGF2YWlsYWJsZSxzY3JlZW5SZXNvbHV0aW9uOjkwMCwxNDQwLGF2YWlsYWJsZVNjcmVlblJlc29sdXRpb246ODM3LDE0NDAsdGltZXpvbmVPZmZzZXQ6MCx0aW1lem9uZTpFdXJvcGUvTGlzYm9uLGNwdUNsYXNzOm5vdCBhdmFpbGFibGUscGxhdGZvcm06TWFjSW50ZWwsd2ViZ2xWZW5kb3JBbmRSZW5kZXJlcjpJbnRlbCBJbmMufkludGVsKFIpIElyaXMoVE0pIFBsdXMgR3JhcGhpY3MgNjQ1LHRvdWNoU3VwcG9ydDowLGZhbHNlLGZhbHNlLGF1ZGlvOjM1LjczODMyOTU5MzA5MjI%3D',
            'accion': '3',
            'ssafe': '',
            'linkHomeURL': ''
        }
        soup = bs4.BeautifulSoup(r.text, 'html.parser')
        items = soup.find_all('input')
        for item in items:
            if item.attrs['name'] in self.login_params and 'value' in item.attrs:  # noqa
                self.login_params[item.attrs['name']] = item.attrs['value']

        r = s.get(
            BASE_URL + "nbp_guard"
        )
        headers = {
            'FETCH-CSRF-TOKEN': '1',
        }
        r = s.post(
            BASE_URL + "nbp_guard",
            headers=headers,
        )
        self.OGC_TOKEN = r.text.split(':')[1]

        # this seems irrelevant but we'll keep it as is
        ts = str(time.time()).split('.')[0]
        r = s.get(
            BASE_URL + "jsp/sanpt/usuarios/login_functions.jsp?_=" + ts,
            headers={
                'OGC_TOKEN': self.OGC_TOKEN,
            }
        )

        ts = str(time.time()).split('.')[0]
        r = s.get(
            BASE_URL + "jsp/sanpt/usuarios/loginForm_novo.jsp?_=" + ts,
            headers={
                'OGC_TOKEN': self.OGC_TOKEN,
            }
        )

        # finding username and password obfuscated parameter names
        matches = re.findall(
            "\'([A-Z0-9]+)\'",
            r.text,
        )
        self.password_param_name = matches[0]
        for match in matches:
            if match != self.password_param_name:
                self.username_param_name = match
                break

    def is_authenticated(self):
        try:
            self.get_page(MAINPAGE)
            return True
        except RedirectedException:
            return False
        return False

    def authenticate(self, user, password):
        logging.debug("authenticating...")

        self.login_params[self.username_param_name] = user
        self.login_params[self.password_param_name] = password
        self.login_params['OGC_TOKEN'] = self.OGC_TOKEN
        s = self.session
        r = s.post(
            url=BASE_URL + LOGIN_PAGE,
            data=self.login_params,
            headers={
                "Origin": BASE_URL,
                "Connection": "close",
                "Referer": BASE_URL + "bepp/sanpt/usuarios/login/0,,,0.shtml?usr="+user,
            }
        )
        #TODO: check if login successful

        # getting next legit url from embedded redirect script
        # not sure if we really need this
        # matches = re.findall(
        #     "\'(.+)\'",
        #     r.text,
        # )
        # url = matches[0]

    def get_account_list(self):
        raise NotImplementedError
 
    def get_account(self, number=0):
        logging.debug("getting account")
        return SantanderAccount(number, self)


class SantanderAccount(Account):
    def __init__(self, number, bank):
        self.number = number
        self.bank = bank

    def get_movements(self):
        s = self.bank.session
        r = s.post(
            url=GETTRANSACTIONS_URL,
            data={
                "OGC_TOKEN": self.bank.OGC_TOKEN,
            }
        )
        transactions = []
        soup = bs4.BeautifulSoup(r.text, "html.parser")

        items = soup.find_all('a', attrs={"class": "tr"})
        for item in items:
            columns = item.find_all('span')
            for col in columns:
                if 'DataValor' in col.attrs['id']:
                    valuedate = col.text
                elif 'DataOperacao' in col.attrs['id']:
                    date = col.text
                elif 'Descricao' in col.attrs['id']:
                    description = col.text
                elif 'Valor' in col.attrs['id']:
                    value = col.text
                elif 'Saldo' in col.attrs['id']:
                    balance = col.text
            transaction = SantanderTransaction(
                date,
                valuedate,
                description,
                value,
            )
            transactions.append(transaction)
        return transactions


class SantanderTransaction(Transaction):
    def parse_value(self, value):
        try:
            # we're expecting Santander value format like 'mmm.ccc,dd EUR'
            # we remove "." characters and then replace "," by "."
            # to convert to float
            valid_value = value.replace('.', '').replace(',', '.')
            return float(valid_value)
        except ValueError:
            return None

    def parse_date(self, value):
        try:
            # we're expecting Santander date format like this 'dd-mm-yyyy'
            # validating and creating a real date object
            valid_date = datetime.strptime(value, '%d-%m-%Y')
            return date(valid_date.year, valid_date.month, valid_date.day)
        except ValueError:
            return None
