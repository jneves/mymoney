# -*- coding: utf-8 -*-

import re
import urllib.request
import urllib.parse
import urllib.error
import ssl
from bs4 import BeautifulSoup
import http.cookiejar
import logging

from datetime import datetime, date
from .bank import Bank
from .account import Account
from .transaction import Transaction

LOGINPAGE = "https://bpinet.bancobpi.pt/BPINET/Login.aspx"
MAINPAGE = "https://bpinet.bancobpi.pt/BPINet_Contas/Movimentos.aspx"
GETTRANSACTIONS_URL = "https://bpinet.bancobpi.pt/BPINet_Contas/Movimentos.aspx"

# These inputs change name often
# Hopefully only a small part of the name we can match to these regexps
# Ex: 'LT_BPINet_wtLT_Layout_Login$block$wtInputsLogin$CS_BPINet_Autenticacao_wt49$block$wtUserId'
USERNAME_PARAM = 'LT_BPINet_wtLT_Layout_Login.*UserId'
# Ex: 'LT_BPINet_wtLT_Layout_Login$block$wtInputsLogin$CS_BPINet_Autenticacao_wt49$block$wtPassword'
PASSWORD_PARAM = 'LT_BPINet_wtLT_Layout_Login.*Password'
# Ex: 'LT_BPINet_wtLT_Layout_Login$block$wtInputsLogin$CS_BPINet_Autenticacao_wt49$block$wtBtnEntrar'
BUTTON_PARAM = 'LT_BPINet_wtLT_Layout_Login.*BtnEntrar'


class RedirectedException(Exception):
    pass


class AuthenticationException(Exception):
    pass


def post_request(url, values):
    data = urllib.parse.urlencode(values)
    req = urllib.request.Request(url, data)
    return urllib.request.urlopen(req)


class BPINet(Bank):
    name = "BPI"
    __OSVSTATE = None
    __VIEWSTATE = None

    def login(self):
        self.start(self.info["user"], self.info["pass"], "cookie.txt")
        self.save_session()

    def start(self, user, password, cookie_file=None):
        self.cookie_file = cookie_file
        # CURRENTLY NOT SUPPORTING SESSION REUSE
        self.load_session(False)
        self.authenticate(user, password)

    def get_page(self, url, parameters={}, allow_redirects=False):
        if self.__OSVSTATE:
            parameters['__OSVSTATE'] = self.__OSVSTATE
            parameters['__VIEWSTATE'] = self.__VIEWSTATE
        d = urllib.parse.urlencode(parameters)
        data = d.encode("utf8")
        f = self.opener.open(url, data)
        if not allow_redirects and f.geturl() != url:
            raise RedirectedException("got "+f.geturl()+" instead of "+url)
        html = f.read()
        return html

    def load_session(self, file_present=True):
        logging.debug("loading cookie from file")
        self.cookiejar = http.cookiejar.LWPCookieJar()

        ctx = ssl.create_default_context()
        if self.ignore_ssl_verication:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        ssl_handler = urllib.request.HTTPSHandler(
            debuglevel=0,
            context=ctx,
        )

        #if file_present:
        #    self.cookiejar.load( filename= self.cookie_file, ignore_discard=True)
        if self.proxy:
            self.opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(self.cookiejar),
                self.proxy,
                ssl_handler,
            )
        else:
            self.opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(self.cookiejar),
                ssl_handler,
            )
            self.opener.addheaders = [
                ('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:79.0) Gecko/20100101 Firefox/79.0'),
                ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'),
                ('Accept-Language', 'en-GB,en;q=0.5'),
                #('Accept-Encoding', 'gzip, deflate'),
                ('Content-Type', 'application/x-www-form-urlencoded'),
                ('Origin', 'https://bpinet.bancobpi.pt'),
                ('DNT', '1'),
                ('Referer', 'https://bpinet.bancobpi.pt/BPINET/login.aspx'),
                ('Upgrade-Insecure-Requests', '1'),
            ]

    def save_session(self):
        logging.debug("saving cookie to file")
        if self.cookie_file is None:
            raise Exception(
                "Cookie filename was not specified on construction"
            )
        self.cookiejar.save(filename=self.cookie_file, ignore_discard=True)

    def is_authenticated(self):
        try:
            self.get_page(MAINPAGE)
            return True
        except RedirectedException:
            return False
        return False

    def authenticate(self, user, password):
        logging.debug("authenticating...")

        def valid_parameter(parameter):
            ''' all char in passwd must be integers
            '''
            if not isinstance(parameter, str):
                parameter = str(parameter)
            for char in parameter:
                try:
                    int(char)
                except ValueError:
                    logging.error('invalid authentication parameter')
                    return False
            return True
        html = self.get_page(LOGINPAGE)
        soup = BeautifulSoup(html, "html.parser")

        # login_inputs = soup.find_all(
        #    "input", attrs={'name': re.compile("UserId|Password")}
        # )
        viewstate_input = soup.find_all('input', attrs={'name': '__VIEWSTATE'})
        if viewstate_input and len(viewstate_input) == 1:
            self.__VIEWSTATE = viewstate_input[0]['value']
        else:
            raise AuthenticationException("Could not get __VIEWSTATE value")
        osvstate_input = soup.find_all('input', attrs={'name': '__OSVSTATE'})
        if osvstate_input and len(osvstate_input) == 1:
            self.__OSVSTATE = osvstate_input[0]['value']
        else:
            raise AuthenticationException("Could not get __OVSTATE value")

        # These inputs change name often.
        # Hopefully the change is just a small part of the string (a number)
        username_param = soup.find_all('input', attrs={'name': re.compile(USERNAME_PARAM)})[0].attrs['name']
        password_param = soup.find_all('input', attrs={'name': re.compile(PASSWORD_PARAM)})[0].attrs['name']
        button_param = soup.find_all('input', attrs={'name': re.compile(BUTTON_PARAM)})[0].attrs['name']

        if valid_parameter(password):
            parameters = {
                username_param: user,
                password_param: password,
                button_param: 'Entrar',
            }

            self.get_page(
                LOGINPAGE,
                parameters,
                True,
            )

        if not self.is_authenticated():
            raise AuthenticationException(
                "Could not authenticate with given data"
            )

    def get_account_list(self):
        raise NotImplementedError

    def get_account(self, number=0):
        logging.debug("getting account")
        return BPINetAccount(number, self)


class BPINetAccount(Account):
    def __init__(self, number, bank):
        self.number = number
        self.bank = bank

    def get_movements(self):
        target_url = GETTRANSACTIONS_URL
        page = self.bank.get_page(target_url)
        soup = BeautifulSoup(page, features="html.parser")
        transactions = []
        movements_lines = soup.find_all('tr')
        for movement_line in movements_lines:
            columns = movement_line.find_all('td')
            movement = []
            for column in columns:
                movement.append(column.get_text().strip())
            if len(movement) > 0:
                transaction = BPITransaction(
                    date=movement[0],
                    valuedate=movement[1],
                    description=movement[2],
                    value=movement[3],
                )
                transactions.append(transaction)

        return transactions


class BPITransaction(Transaction):
    def parse_value(self, value):
        try:
            # we're expecting BPINet value format like 'mmm.ccc,dd EUR'
            # we remove "." characters and then replace "," by "."
            # to convert to float
            valid_value = value.replace('.', '').replace(',', '.')
            valid_value = valid_value.replace(' EUR', '')
            return float(valid_value)
        except ValueError:
            return None

    def parse_date(self, value):
        try:
            # we're expecting BPINet date format like this 'dd-mm-yyyy'
            # validating and creating a real date object
            valid_date = datetime.strptime(value, '%d-%m-%Y')
            return date(valid_date.year, valid_date.month, valid_date.day)
        except ValueError:
            return None
