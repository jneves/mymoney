# -*- coding: utf-8 -*-

from bank import Bank
from account import Account

import urllib, urllib2
from BeautifulSoup import BeautifulSoup
import cxdo_auth
import cookielib
import logging
import re
import os

from datetime import date, timedelta

LOGINSTARTPAGE= "https://www.millenniumbcp.pt/secure/pt/90/9021_1.jhtml"
LOGINPAGE= "https://www.millenniumbcp.pt/secure/pt/90/9021_2.jhtml?_DARGS=/secure/pt/90/9021_2.jhtml"
MAINPAGE= "https://www.millenniumbcp.pt/secure/10/1098_1.jhtml"
ACCOUNTINDEX="https://www.millenniumbcp.pt/secure/10/1020_1.jhtml"
STATEMENT=""

class RedirectedException( Exception ):
    pass
class AuthenticationException( Exception):
    pass

def post_request(url, values):
    data = urllib.urlencode(values)
    req = urllib2.Request(url, data)
    return urllib2.urlopen(req)

class BCP(Bank):
    def login(self):
        self.start(self.info["user"], self.info["pass"], "cookie.txt")
        self.save_session()

    def start(self, user, password, cookie_file=None):
        if cookie_file:
            self.cookie_file= cookie_file
            self.load_session(os.path.isfile(cookie_file))
            self.authenticate(user, password)

    def get_page(self, url, parameters={}, allow_redirects=False):
        d= urllib.urlencode(parameters)
        f= self.opener.open(url, data=d)
        if not allow_redirects and f.geturl()!=url:
            raise RedirectedException("got "+f.geturl()+" instead of "+url)
        html= f.read()
        #if not get_cxdo_version(html) == CXDO_VERSION:
            #logging.warn('CXDO site version differs from expected. got %r, expected %r', get_cxdo_version(html), CXDO_VERSION)
        return html

    def load_session(self, file_present=True):
        logging.debug("loading cookie from file")
        self.cookiejar= cookielib.LWPCookieJar( )
        #if file_present:
        #    self.cookiejar.load( filename= self.cookie_file, ignore_discard=True)
        self.opener= urllib2.build_opener( urllib2.HTTPCookieProcessor(self.cookiejar) )

    def save_session(self):
        logging.debug("saving cookie to file")
        if self.cookie_file is None:
            raise Exception("Cookie filename was not specified on construction")
        self.cookiejar.save( filename= self.cookie_file, ignore_discard=True)

    def is_authenticated(self):
        try:
            html= self.get_page(MAINPAGE)
            return True
        except RedirectedException as e:
            print e
            return False

    def authenticate(self, user, password):
        logging.debug("authenticating...")

        html = self.get_page( LOGINSTARTPAGE, {"mlUsr": user}, True ) #needed to set
        print html
        # extract positions
        soup = BeautifulSoup(html)
        row = soup.find('tr', id="trid_1")
        chars = []
        for each in row.findAll('strong'):
            chars.append(each.string[0])
        print chars
        print self.info["pass"][int(chars[0])-1]
        print self.info["pass"][int(chars[1])-1]
        print self.info["pass"][int(chars[2])-1]
        html = self.get_page(LOGINPAGE, {"onlyPwd":1, "_D:login":" ", "loginAux": self.info["user"], "_D:loginAux":" ", "dig1": self.info["pass"][int(chars[0])-1], "_D:dig1": " ", "dig2": self.info["pass"][int(chars[1])-1], "_D:dig2":" ", "dig3": self.info["pass"][int(chars[2])-1], "_D:dig3": " ","/bcp/cidadebcp/90/F9021_Login.submit2": "", "_D:/bcp/cidadebcp/90/F9021_Login.submit2": " ","x": 47, "y": 11}, True)

        if not self.is_authenticated():
            raise AuthenticationException("Could not authenticate with given data")

    def get_account_list(self):
        html = self.get_page(ACCOUNTINDEX)
        soup = BeautifulSoup(html)
        select = soup.find('table', id='accountTable')
        res = []
        for option in select.findAll('tr')[1:]:
            tds = option.findAll('td')

            id = tds[0].input['value']
            desc = tds[2].string.replace('&nbsp;', '')
            res.append((id,desc))
        return res

    def get_account(self, number=0):
        return CGDCDAccount(number, self)

class BCPAccount(Account):
    def __init__(self, number, bank):
        self.number = number
        self.bank = bank
        self.set_account()        

    def set_account(self):
        self.html = self.bank.get_page(ACCOUNTINDEX, {"accountIndex": self.number, "changeActiveAccount" : 1})

    def get_information(self):
        self.set_account()
        soup = BeautifulSoup(self.html)
        l = soup.find('form', id='accountInfoForm').findAll('tr')
        return { "currency": l[0].findAll('td')[1].string,
                 "type": l[1].findAll('td')[1].string,
                 "nib": l[2].findAll('td')[1].string,
                 "iban": l[4].findAll('td')[1].string,
                 "swift": l[5].findAll('td')[1].string,
                 "accounting": l[8].findAll('td')[1].string,
                 "available": l[8].findAll('td')[3].string
                 }

    def get_balance(self):
        self.set_account()
        soup = BeautifulSoup(self.html)
        l = soup.find('form', id='accountInfoForm').findAll('tr')
        return l[8].findAll('td')[3].string

    def get_movements(self, start_date=(date.today()-timedelta(weeks=1)), end_date=date.today, limit=100):
        self.set_account()
        soup = BeautifulSoup(self.bank.get_page(STATEMENT))
        l = soup.find('div', id='globalStatementAjaxDiv').findAll('tr')
        l = l[1:]
        res = []
        for line in l:
            res_inner = []
            for cell in line.findAll('td'):
                if cell.string:
                    res_inner.append(cell.string.strip())
                elif cell.a:
                    if cell.a.string:
                        res_inner.append(cell.a.string.strip())
            res.append(res_inner)
        return res

class CGDCaixaBanking(Bank):
    pass

class CGDCBAccount(Account):
    pass

