# -*- coding: utf-8 -*-

from bank import Bank
from account import Account

import urllib, urllib2
from BeautifulSoup import BeautifulSoup
import cookielib
import logging
import re
import os
import time

USERLOGINPAGE = "https://net24.montepio.pt/Net24-Web/func/acesso/net24pLoginTV.jsp"
BASEDOMAIN = "https://net24.montepio.pt"
MAINPAGE = "https://net24.montepio.pt/Net24-Web/func/homePages/executa.jsp?pagInic=1&selectedNode=100"
ACCOUNTINDEX ="https://net24.montepio.pt/Net24-Web/func/contasordem/posicaoIntegrada.jsp?selectedNode=101"

class RedirectedException( Exception ):
    pass
class AuthenticationException( Exception):
    pass

class MontepioNet24(Bank):
    def login(self):
        logging.info("Loging in")
        self.start(self.info["user"], self.info["pass"], "montepio_cookie.txt")
        self.save_session()

    def start(self, user, password, cookie_file=None):
        if cookie_file:
            self.cookie_file= cookie_file
            self.load_session(os.path.isfile(cookie_file))
            if not self.is_authenticated():
                logging.info("saved cookie session has expired")
                self.authenticate(user, password)

    def authenticate(self, user, password):
        # POST user
        values = {
            'loginid_IN' : user,
            'pageCWS' : 'https://www.montepio.pt/SitePublico/pt_PT/particulares.page',
        }
        res1 = self.get_page( USERLOGINPAGE, parameters=values )

        #get the action for the next form
        x = re.findall( r"Net24-Web/func/VLNP/.+?.jsp", res1)
        url = '/'.join((BASEDOMAIN, x[0]))

        # translate password/pin
        pass_translit = {}
        new_pass = password
        for m in re.finditer(r"<input.*?value=\"(\d)\".*?onclick=\"doclick\('(\w+)'\);\".*?>", res1):
            key = m.group(1)
            value = m.group(2)
            pass_translit[ key ] = value
            new_pass = new_pass.replace(key,value)

        # POST pin
        values = {
            'pin1_IN' : new_pass,
        }
        self.opener.addheaders.append(
                ('Referer','https://net24.montepio.pt/Net24-Web/func/acesso/net24pLoginTV.jsp'),
        )
        res2 = self.get_page(url, parameters=values, allow_redirects=True )

    def load_session(self, file_present=True):
        logging.debug("loading cookie from file")
        self.cookiejar= cookielib.LWPCookieJar( )
        #if file_present:
        #    self.cookiejar.load( filename= self.cookie_file, ignore_discard=True)
        self.opener= urllib2.build_opener( urllib2.HTTPCookieProcessor(self.cookiejar) )
        self.opener.addheaders = [
                ('User-agent','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.21 Safari/535.7'),
                ('Origin', 'https://net24.montepio.pt'),
            ]

    def save_session(self):
        logging.debug("saving cookie to file")
        if self.cookie_file is None:
            raise Exception("Cookie filename was not specified on construction")
        self.cookiejar.save( filename= self.cookie_file, ignore_discard=True)

    def get_page(self, url, parameters={}, allow_redirects=False):
        d= urllib.urlencode(parameters)
        f= self.opener.open(url, data=d)
        if not allow_redirects and f.geturl()!=url:
            raise RedirectedException("got "+f.geturl()+" instead of "+url)
        html= f.read()
        #if not get_cxdo_version(html) == CXDO_VERSION:
            #logging.warn('CXDO site version differs from expected. got %r, expected %r', get_cxdo_version(html), CXDO_VERSION)
        return html

    def is_authenticated(self):
        try:
            html= self.get_page(MAINPAGE)
            return True
        #except RedirectedException:
        except:
            return False

    def get_account_list(self):
        html = self.get_page(ACCOUNTINDEX)
        #count number of accounts
        contas = re.findall(r"conta\d\d\d", html)
        soup = BeautifulSoup(html)
        contas_info = []
        for i in range( len(contas) ):
            conta_id = "%.3d" % i
            select = soup.find('tr', { 'id' : "c" + conta_id } );
            conta = []
            if select:
                for td in select.findAll( 'td', { 'class' : 'tdClass1'} ):
                    if td.a:
                        content = td.a.string
                    else:
                        content = td.string
                    conta.append(content)
            contas_info.append( ( conta_id, ' - '.join(conta) ) )
        return contas_info

    def get_account(self, number=0):
        return MontepioN24Account(number, self)

class MontepioN24Account(Account):
    def __init__(self, number, bank):
        self.number = number
        self.bank = bank

    def get_information(self):
        url = "https://net24.montepio.pt/Net24-Web/func/contasordem/consultaNIBIBAN.jsp"
        html = self.bank.get_page( url , parameters={ 'selCtaOrdem' : self.number } )
        #info = re.findall( r"txtCampo.*?>(.*?):<.*?>.*?<.*?txtLabel.*?>(.*?)<", html, re.M)
        info = re.findall( r"txtCampo.*?>(.*?):<.*?>.*?<.*?txtLabel.*?>(.*?)<", html, re.M + re.DOTALL)
        return info





