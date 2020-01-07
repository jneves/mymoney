# -*- coding: utf-8 -*-
import requests
import json
import time
import date
import logging

import dateutil.parser
from .bank import Bank
from .transaction import Transaction


BASE_URL = "https://www.myedenred.pt/edenred-customer/api/"
LOGIN_URL = BASE_URL + "authenticate/default?appVersion=1.0&appType=PORTAL&channel=WEB"


GETCARD_TRANSACTIONS_URL = BASE_URL + "protected/card/<card_id>/accountmovement?_=<timestamp>&appVersion=1.0&appType=PORTAL&channel=WEB" # noqa
GETCARDS_URL = BASE_URL + 'protected/card/list?_=<timestamp>&appVersion=1.0&appType=PORTAL&channel=WEB' # noqa


class AuthenticationException(Exception):
    pass


class MyEdenred(Bank):
    name = "MyEdenred"
    __OSVSTATE = None
    __VIEWSTATE = None

    def login(self):
        self.start()  # load cookies and parameters
        self.authenticate(self.info["user"], self.info["pass"])

    def start(self, cookie_file=None):
        # CURRENTLY NOT SUPPORTING SESSION REUSE
        self.load_session(False)

    def load_session(self, file_present=True):
        self.session = requests.Session()

    def is_authenticated(self):
        raise NotImplementedError

    def authenticate(self, user, password):
        """ Actual authentication. Needs variables previously loaded """
        logging.debug("authenticating...")

        self.login_params = {
            "userId": user,
            "password": password,
            "rememberMe": True
        }
        s = self.session
        r = s.post(
            url=LOGIN_URL,
            json=self.login_params,
            verify=not self.debug,
        )
        # TODO: check if login successful
        try:
            if r.status_code == 200:
                response = json.loads(r.text)
                if 'token' in response['data']:
                    self.token = response['data']['token']
                else:
                    raise AuthenticationException(r.text)
        except Exception():
            raise AuthenticationException(r.text)

    def get_account_list(self):
        raise NotImplementedError

    def get_account(self, number=0):
        raise NotImplementedError

    def get_card_list(self):
        s = self.session
        cards = []
        ts = str(time.time()).split('.')[0]
        r = s.get(
            headers={
                'Authorization': self.token,
            },
            url=GETCARDS_URL.replace('<timestamp>', ts),
        )
        response = json.loads(r.text)
        for card_info in response['data']:
            card = MyEdenredCard(self, card_info)
            cards.append(card)
        return cards

    def get_card(self, card_id):
        logging.debug("getting card")
        cards = self.get_card_list()
        for card in cards:
            if card.id == card_id:
                return card


class MyEdenredCard():

    def __init__(self, bank, card_info):
        self.bank = bank
        self.id = card_info['id']
        self.number = card_info['number']
        self.owner_name = card_info['ownerName']
        self.status = card_info['status']
        self.full_data = card_info

    def get_movements(self):
        s = self.bank.session
        transactions = []
        ts = str(time.time()).split('.')[0]
        r = s.get(
            headers={
                'Authorization': self.bank.token,
            },
            url=GETCARD_TRANSACTIONS_URL.replace(
                    '<card_id>', str(self.id)).replace('<timestamp>', ts),
        )
        response = json.loads(r.text)
        self.account_info = response['data']['account']
        self.movement_list = response['data']['movementList']
        for movement in self.movement_list:
            transaction = MyEdenredTransaction(movement)
            transactions.append(transaction)
        return transactions


class MyEdenredTransaction(Transaction):

    balance = None

    def __init__(self, movement_info):
        super().__init__(
            date=movement_info['transactionDate'],
            valuedate=movement_info['transactionDate'],
            description=movement_info['transactionName'],
            value=movement_info['amount'],
        )
        self.balance = movement_info['balance']

    def parse_date(self, value):
        # we're expecting na iso formated date and time
        # we're only getting the date for now
        valid_date = dateutil.parser.parse(value)
        return date(valid_date.year, valid_date.month, valid_date.day)
