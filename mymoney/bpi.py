# -*- coding: utf-8 -*-

from .bank import Bank
from .account import Account
from .transaction import Transaction

import urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse
from bs4 import BeautifulSoup
import http.cookiejar
import logging
import os

from datetime import datetime,date,timedelta


LOGINPAGE= "https://www.bpinet.pt/verificaMCF.asp"
MAINPAGE= "https://www.bpinet.pt/Frame.asp"
ACCOUNTINDEX="https://www.bpinet.pt/areaInf/consultas/Movimentos/movimentosIeA.asp"
STATEMENT="https://www.bpinet.pt/areaInf/consultas/Movimentos/Movimentos.asp" # only recent transactions
GETTRANSACTIONS_URL="https://www.bpinet.pt/areaInf/consultas/Movimentos/MovimentosIeA.asp"
GETTRANSACTIONS_NEXTPAGE_URL="https://www.bpinet.pt/areaInf/consultas/Movimentos/MovimentosIeA.asp?Op=2"
GETTRANSACTIONS_PARAMETERS={'h_MontanteSup': '', 'tipo_servico': '', 'Montante_Inf': '', 'eAno': '', 'tipo_mov': '', 'contaCorrente': '|NR|', 'Montante_Sup': '', 'h_MontanteInf': '', 'sAno': '', 'h_TipoServ': '', 'sMes': '', 'eDia': '', 'eMes': '', 'sDia': ''}



class RedirectedException( Exception ):
    pass
class AuthenticationException( Exception):
    pass

def post_request(url, values):
    data = urllib.parse.urlencode(values)
    req = urllib.request.Request(url, data)
    return urllib.request.urlopen(req)

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
        d= urllib.parse.urlencode(parameters)
        data = d.encode("utf8")
        f= self.opener.open(url, data)
        if not allow_redirects and f.geturl()!=url:
            raise RedirectedException("got "+f.geturl()+" instead of "+url)
        html= f.read()
        return html

    def load_session(self, file_present=True):
        logging.debug("loading cookie from file")
        self.cookiejar= http.cookiejar.LWPCookieJar( )
        #if file_present:
        #    self.cookiejar.load( filename= self.cookie_file, ignore_discard=True)
        if self.proxy:
            self.opener= urllib.request.build_opener( urllib.request.HTTPCookieProcessor(self.cookiejar),self.proxy )
        else:
            self.opener= urllib.request.build_opener( urllib.request.HTTPCookieProcessor(self.cookiejar) )

    def save_session(self):
        logging.debug("saving cookie to file")
        if self.cookie_file is None:
            raise Exception("Cookie filename was not specified on construction")
        self.cookiejar.save( filename= self.cookie_file, ignore_discard=True)

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

        if  valid_parameter(password):
            self.get_page( LOGINPAGE, {"USERID": user,"PASSWORD": password},True )
            
        if not self.is_authenticated():
            raise AuthenticationException("Could not authenticate with given data")

    def get_account_list(self):
        logging.debug("getting account list")
        html = self.get_page(ACCOUNTINDEX,{},True)
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

    def get_movements(self, start_date=(date.today()-timedelta(weeks=1)), end_date=date.today(), limit=None):
        target_url=GETTRANSACTIONS_URL
        post_content=GETTRANSACTIONS_PARAMETERS
        post_content['contaCorrente']="%s|NR" % self.number
        post_content['sDia']=start_date.day
        post_content['sMes']=start_date.month
        post_content['sAno']=start_date.year
        post_content['eDia']=end_date.day
        post_content['eMes']=end_date.month
        post_content['eAno']=end_date.year
        
        transactions = []
        while True:
            soup = BeautifulSoup(self.bank.get_page(target_url,post_content,allow_redirects=True)) 
            table = soup.findAll('table',limit=6)[3]
            lines = table.findAll('tr')
            for line in lines:
                columns = line.findAll('td')
                res_inner = []
                for col in columns:
                    if col.string != None:
                        res_inner.append(col.string.strip())
                if res_inner[0] != "Data Mov.": #skipping title line
                    transaction = BPITransaction(date=res_inner[0],valuedate=res_inner[1],description=res_inner[2],value=res_inner[3])
                    transactions.append(transaction)
                    
            if "Datas Anteriores" in str(soup):
                #FIX: this is an ungly hack because the line below stopped working
                #if soup.find('input')['value']=='Datas Anteriores':
                target_url=GETTRANSACTIONS_NEXTPAGE_URL
            else:
                break

        return transactions



class BPITransaction(Transaction):
    def parse_value(self,value):
        try:
            # we're expecting BPINet value format like 'mmm.ccc,dd'
            # we remove "." characters and then replace "," by "." to convert to float
            valid_value = value.replace('.','').replace(',','.')
            return float(valid_value)
        except ValueError:
            return None
            
    def parse_date(self,value):
        try:
            # we're expecting BPINet date format like this 'dd-mm-yyyy'
            # validating and creating a real date object
            valid_date = datetime.strptime(value, '%d-%m-%Y')
            return date(valid_date.year,valid_date.month,valid_date.day)
        except ValueError:
            return None

