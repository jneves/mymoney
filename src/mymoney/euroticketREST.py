#!/usr/bin/env python
# This is heavely based on https://github.com/marmelo/euroticket-alacard-rest-api
# -*- coding: utf-8 -*-

from .bank import Bank
from .account import Account
from .transaction import Transaction

import hmac
import hashlib
import json
import urllib.request
from datetime import datetime,date

BASE_URL = 'https://www.euroticket-alacard.pt'
AUTH_URL = '/alc/rsvc/login'
DATA_URL = '/alc/rsvc/getBalanceAndTransactions'
ENCODING = 'UTF-8'

SYSTEM = {
    'appId': '5000',
    'appVersion': '1.0.1',
    'deviceId': 'XXX',
    'deviceModel': 'YYY',
    'osId': 'android',
    'osVersion': '4.1.1',
    'language': 'pt'
}


    
    





class EuroTicketREST(Bank):
    name = "EuroTicket"


    def login(self):
        # authentication
        data = dict(SYSTEM, **{
            'username': self.info["user"],
            'hashPin': self._hmacSHA256(self.info["user"], self.info["pass"])
        })
    
        res = self.post(BASE_URL + AUTH_URL, data)
    
        if res['status']['errorCode'] != 0:
            raise Exception(res['status']['errorMsg'])
        self.securityToken = res['securityToken']

    def _hmacSHA256(self,username, password):
        """Calculate authentication hash."""
        return hmac.new(b'JFq7JpxvRoE1XjqTE6qNKfvcddA5V43A',
                    msg=(SYSTEM['deviceId'] + username + password).encode(ENCODING),
                    digestmod=hashlib.sha256).hexdigest()
    def post(self,url, data):
        """Perform a JSON HTTP POST request."""
        req = urllib.request.Request(url, json.dumps(data).encode(ENCODING), { 'Content-Type': 'application/json' })
        res = urllib.request.urlopen(req)
        return json.loads(res.read().decode(ENCODING))


class EuroTicketRESTAccount(Account):

    def __init__(self,bank):
        self.bank = bank

    def get_movements(self):
        # balance and movements
        data = dict(SYSTEM, **{
            'securityToken': self.bank.securityToken
        })
    
        res = self.bank.post(BASE_URL + DATA_URL, data)
    
        if res['status']['errorCode'] != 0:
            raise Exception(res['status']['errorMsg'])
        movements = res["movements"]
        transactions = []
        for movement in movements:
            print(movement)
            transaction = EuroTicketRESTTransaction(date=movement['date'],valuedate=movement['date'],description=movement['description'],value=movement['value'])
            transactions.append(transaction)
        return transactions

    
class EuroTicketRESTTransaction(Transaction):
    def parse_value(self,value):
        try:
            valid_value = value
            return float(valid_value)
        except ValueError:
            return None
            
    def parse_date(self,value):
        try:
            # we're expecting date format like this 'mm-dd'
            valid_date = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f%z')
            return date(valid_date.year,valid_date.month,valid_date.day)
        except ValueError:
            return None

