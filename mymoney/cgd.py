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

CXDO_VERSION= "v56_8_0_WS_v5_123_1"
LOGINSTARTPAGE= "https://caixadirecta.cgd.pt/CaixaDirecta/loginStart.do"
LOGINPAGE= "https://caixadirecta.cgd.pt/CaixaDirecta/login.do"
MAINPAGE= "https://caixadirecta.cgd.pt/CaixaDirecta/profile.do"

class RedirectedException( Exception ):
    pass
class AuthenticationException( Exception):
    pass

def post_request(url, values):
    data = urllib.urlencode(values)
    req = urllib2.Request(url, data)
    return urllib2.urlopen(req)

class CGDCaixaDirecta(Bank):
    def login(self):
        self.start(self.info["user"], self.info["pass"], "cookie.txt")
        self.save_session()

    def start(self, user, password, cookie_file=None):
        if cookie_file:
            self.cookie_file= cookie_file
            self.load_session(os.path.isfile(cookie_file))
            if not self.is_authenticated():
                logging.info("saved cookie session has expired")
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
        except RedirectedException:
            return False

    def authenticate(self, user, password):
        logging.debug("authenticating...")

        def valid_parameter(parameter):
            ''' all char in user and passwd must be integers
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

        if valid_parameter(user) and valid_parameter(password):
            l1_html= self.get_page( LOGINSTARTPAGE, {"USERNAME": user} ) #needed to set
            auth_data= cxdo_auth.parameters(l1_html, user,password)
            l2_html= self.get_page( LOGINPAGE, auth_data, allow_redirects=True)

        if not self.is_authenticated():
            raise AuthenticationException("Could not authenticate with given data")

    def get_account_list(self):
        ACCOUNTINDEX="https://caixadirecta.cgd.pt/CaixaDirecta/accountInfo.do"
        html = self.get_page(ACCOUNTINDEX)
        soup = BeautifulSoup(html)
        select = soup.find('select', id='accountIndex')
        res = []
        for option in select.findAll('option'):
            res.append((option['value'], option.string))
        return res

class CGDCDAccount(Account):
    pass

class CGDCaixaBanking(Bank):
    pass

class CGDCBAccount(Account):
    pass

