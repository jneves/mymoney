# -*- coding: utf-8 -*-

from bank import Bank
from account import Account

import urllib, urllib2
from BeautifulSoup import BeautifulSoup
import cookielib
import logging
import re
import os

from datetime import date, timedelta


#LOGINSTARTPAGE= "https://caixadirecta.cgd.pt/CaixaDirecta/loginStart.do"
LOGINPAGE= "https://www.bpinet.pt/verificaMCF.asp"
MAINPAGE= "https://www.bpinet.pt/Frame.asp"
ACCOUNTINDEX="https://www.bpinet.pt/areaInf/consultas/Movimentos/movimentosIeA.asp"
STATEMENT="https://www.bpinet.pt/areaInf/consultas/Movimentos/Movimentos.asp" # only recent transactions
#GETTRANSACTIONS_URL="https://www.bpinet.pt/areaInf/consultas/Movimentos/MovimentosIeA.asp"
#GETTRANSACTIONS_CONTENT="contaCorrente=$ACCOUNT%7CNR%7C&sDia=$sDay&sMes=$sMonth&sAno=$sYear&eDia=$eDay&eMes=$eMonth&eAno=$eYear&Montante_Inf=&Montante_Sup=&tipo_mov=&tipo_servico=&h_MontanteInf=&h_MontanteSup=&h_TipoServ="







class RedirectedException( Exception ):
    pass
class AuthenticationException( Exception):
    pass

def post_request(url, values):
    data = urllib.urlencode(values)
    req = urllib2.Request(url, data)
    return urllib2.urlopen(req)

class BPINet(Bank):
    name = "BPI"

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

        if  valid_parameter(password):
            l1_html= self.get_page( LOGINPAGE, {"USERID": user,"PASSWORD": password},True )
            
        if not self.is_authenticated():
            raise AuthenticationException("Could not authenticate with given data")

    def get_account_list(self):
        logging.debug("getting account list")
        html = self.get_page(ACCOUNTINDEX,{},True)
        soup = BeautifulSoup(html)
        select = soup.find('select', id='contaCorrente')
        res = []
        for option in select.findAll('option'):
            res.append((option['value'], option.string)) #todo: value has extra characters. remove them 
        return res

    def get_account(self, number=0):
        logging.debug("getting account")
        return BPINetAccount(number, self)

class BPINetAccount(Account):
    def __init__(self, number, bank):
        self.number = number
        self.bank = bank

    def get_movements(self, start_date=(date.today()-timedelta(weeks=1)), end_date=date.today, limit=100):
        # todo: add date parameters and get all pages
        print "get_movements"
        soup = BeautifulSoup(self.bank.get_page(STATEMENT,{},True)) # todo: add date parameters
        table = soup.findAll('table',limit=6)[5]
        lines = table.findAll('tr')
        res = []
        for line in lines:
            columns = line.findAll('td')
            res_inner = []
            for col in columns:
                res_inner.append(col.string.strip())
                res.append(res_inner)
        return res

