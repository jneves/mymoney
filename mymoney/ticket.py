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


LOGINPAGE= "https://www.unibancoconnect.pt/login.aspx"
MAINPAGE= "https://www.unibancoconnect.pt/Main.htm"
STATEMENT="https://www.unibancoconnect.pt/Consultas/UltimosMovimentos.aspx" # only recent transactions

class RedirectedException( Exception ):
    pass
class AuthenticationException( Exception):
    pass

def post_request(url, values):
    data = urllib.urlencode(values)
    req = urllib2.Request(url, data)
    return urllib2.urlopen(req)

class TicketRestaurant(Bank):
    name = "TicketRestaurant"

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
        if parameters != None and len(parameters.keys()) > 0:
            d= urllib.parse.urlencode(parameters)
            data = d.encode("utf8")
            f= self.opener.open(url, data)
        else:
            f= self.opener.open(url)
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
        return False

    def authenticate(self, user, password):
        logging.debug("authenticating...")

        def valid_parameter(parameter):
            ''' all char in password and user must be integers (card number...)
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

        if  valid_parameter(password) and valid_parameter(user):
            first_load_login=self.get_page(LOGINPAGE)
            soup = BeautifulSoup(first_load_login)
            element=soup.findAll(id='__VIEWSTATE')[0]
            view_state_value = element["value"]
            element=soup.findAll(id='__EVENTVALIDATION')[0]
            event_validation_value = element["value"]
            self.get_page( LOGINPAGE, {"__EVENTTARGET": "ctl00$Conteudo$BtnConfirmar","__EVENTARGUMENT":"","__LASTFOCUS":"","__VIEWSTATE": view_state_value,"__EVENTVALIDATION": event_validation_value,"ctl00$Conteudo$TxtUserCard": user,"ctl00$Conteudo$TxtPwd": password},True )
            #TODO: validate authentication

class TicketRestaurantAccount(Account):
    def __init__(self, bank):
        self.bank = bank

    def get_movements(self):
        target_url=STATEMENT
        
        transactions = []
        while True:
            soup = BeautifulSoup(self.bank.get_page(target_url,None,allow_redirects=True))
            soup = soup.findAll(id='ctl00_Conteudo_PanelConteud')[0]            
            table = soup.findAll('table')[1]
            lines = table.findAll('tr')

            for line in lines:
                columns = line.findAll('td')
                res_inner = []
                for col in columns:
                    if col.string != None:
                        res_inner.append(col.string.strip())
                    else:
                        res_inner.append(None)
                if res_inner[0] != "Data": #skipping title line
                    value = res_inner[2]
                    if value == None:
                        value = res_inner[3]
                    else:
                        value = "-"+value
                    transaction = TicketRestaurantTransaction(date=res_inner[0],valuedate=res_inner[0],description=res_inner[1],value=value)
                    transactions.append(transaction)

            return transactions



class TicketRestaurantTransaction(Transaction):
    def parse_value(self,value):
        try:
            # we're expecting value format like 'mmm.ccc,dd' (not really sure about the mmm part)
            # we remove "." characters and then replace "," by "." to convert to float
            valid_value = value.replace('.','').replace(',','.')
            return float(valid_value)
        except ValueError:
            return None
            
    def parse_date(self,value):
        try:
            # we're expecting date format like this 'mm-dd'
			# we are going to guess the year... which will most likely fail at the start of the year...
			#TODO: fix this... if possible...
            # validating and creating a real date object
            now = datetime.now()
            valid_date = datetime.strptime(value, '%m-%d')
            if valid_date.month > now.month:
                # trying not to fail start of year... will fail if transactions are really old...
                valid_date = datetime(now.year-1,valid_date.month,valid_date.day,0,0)
            else:
                valid_date = datetime(now.year,valid_date.month,valid_date.day,0,0)
                    
            return date(valid_date.year,valid_date.month,valid_date.day)
        except ValueError:
            return None

