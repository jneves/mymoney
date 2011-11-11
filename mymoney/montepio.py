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
PINLOGINPAGE = "https://net24.montepio.pt/Net24-Web/func/VLNP/1197592006-1196197144.jsp"
BASEDOMAIN = "https://net24.montepio.pt"

class MontepioNet24(Bank):
    def login(self):
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
        self.cookiejar= cookielib.LWPCookieJar( )
        self.opener= urllib2.build_opener( urllib2.HTTPCookieProcessor(self.cookiejar) )

        values = {
            'loginid_IN' : user,
            'pageCWS' : 'https://www.montepio.pt/SitePublico/pt_PT/particulares.page',
        }
        data = urllib.urlencode(values)
        f = self.opener.open(USERLOGINPAGE, data=data)
        res1 = f.read()

        #req = urllib2.Request(url, data)
        #res1 = urllib2.urlopen(req).read()

        #print res1 
        #print repr( self.cookiejar )

        #get the action for the next form
        x = re.findall( r"Net24-Web/func/VLNP/.+?.jsp", res1)
        #print repr(x)
        url = '/'.join((BASEDOMAIN, x[0]))
        #print url

        # translate password/pin
        pass_translit = {}
        new_pass = password
        for m in re.finditer(r"<input.*?value=\"(\d)\".*?onclick=\"doclick\('(\w+)'\);\".*?>", res1):
            key = m.group(1)
            value = m.group(2)
            pass_translit[ key ] = value
            new_pass = new_pass.replace(key,value)

        #print repr( [ pass_translit, password, new_pass] )

        # POST pin
        values = {
            'pin1_IN' : new_pass,
        }
        data = urllib.urlencode(values)
        self.opener.addheaders = (
                ('User-agent','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.21 Safari/535.7'),
                ('Referer','https://net24.montepio.pt/Net24-Web/func/acesso/net24pLoginTV.jsp'),
                ('Origin', 'https://net24.montepio.pt'),
            )
        #print repr( self.opener.addheaders )
        f = self.opener.open( url, data=data )
        res2 = f.read()
        #print repr( f.info().headers )
        #print res2 

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
        return True
