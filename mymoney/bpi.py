# -*- coding: utf-8 -*-

import urllib.request
import urllib.parse
import urllib.error
from bs4 import BeautifulSoup
import http.cookiejar
import logging
import re

from datetime import datetime, date
from .bank import Bank
from .account import Account
from .transaction import Transaction

DEBUG = True
LOGINPAGE = "https://bpinet.bancobpi.pt/BPINET/Login.aspx"
MAINPAGE = "https://bpinet.bancobpi.pt/BPINet_Contas/Movimentos.aspx"
GETTRANSACTIONS_URL = "https://bpinet.bancobpi.pt/BPINet_Contas/Movimentos.aspx"

USERNAME_PARAM = 'LT_BPINet_wtLT_Layout_Login$block$wtInputsLogin$CS_BPINet_Autenticacao_wt49$block$wtUserId'
PASSWORD_PARAM = 'LT_BPINet_wtLT_Layout_Login$block$wtInputsLogin$CS_BPINet_Autenticacao_wt49$block$wtPassword'
BUTTON_PARAM = 'LT_BPINet_wtLT_Layout_Login$block$wtInputsLogin$CS_BPINet_Autenticacao_wt49$block$wtBtnEntrar'


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
        if DEBUG:
            with open("response.html", 'w') as fo:
                fo.write(html.decode('utf8'))
        return html

    def load_session(self, file_present=True):
        logging.debug("loading cookie from file")
        self.cookiejar = http.cookiejar.LWPCookieJar()
        #if file_present:
        #    self.cookiejar.load( filename= self.cookie_file, ignore_discard=True)
        if self.proxy:
            self.opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(self.cookiejar),
                self.proxy,
            )
        else:
            self.opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(self.cookiejar),
            )

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

        if valid_parameter(password):
            parameters = {
                USERNAME_PARAM: user,
                PASSWORD_PARAM: password,
                BUTTON_PARAM: 'Entrar',
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
        logging.debug("getting account list")
        html = self.get_page(ACCOUNTINDEX, {}, True)
        soup = BeautifulSoup(html)
        select = soup.find('select', id='contaCorrente')
        res = []
        for option in select.findAll('option'):
            res.append((option['value'][:-4], option.string)) # I'm removing "|NR|" from the end of the account number but I'm not sure what this is
        return res

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
