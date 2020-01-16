# -*- coding: utf-8 -*-
import requests
import bs4
import time
import re
import logging

from datetime import datetime, date
from .bank import Bank
from .account import Account
from .transaction import Transaction


BASE_URL = "https://www.particulares.santandertotta.pt/"
LOGIN_PAGE = "bepp/sanpt/usuarios/login/?"
GETTRANSACTIONS_URL = BASE_URL + "/bepp/sanpt/cuentas/listadomovimientoscuenta/0,,,0.shtml" # noqa

GETCARDS_URL = BASE_URL + 'bepp/sanpt/tarjetas/listadomovimientostarjetadebito/0,,,0.shtml' # noqa
GETCARD_STATEMENTS_URL = BASE_URL + 'bepp/sanpt/tarjetas/listadomovimientosadebitotarjetacredito/?' # noqa
GETCARD_TRANSACTIONS_URL = BASE_URL + 'bepp/sanpt/tarjetas/consultamovimientosextractotarjetacredito/?' # noqa


class AuthenticationException(Exception):
    pass


class Santander(Bank):
    name = "Santander"
    __OSVSTATE = None
    __VIEWSTATE = None

    def login(self):
        self.start()  # load cookies and parameters
        self.authenticate(self.info["user"], self.info["pass"])

    def start(self, cookie_file=None):
        # CURRENTLY NOT SUPPORTING SESSION REUSE
        self.load_session(False)

    def load_session(self, file_present=True):
        """
        Loads some variables and tokens required for the
        authentication call.
        """
        # For logging in into Santander, we need to find the obfuscated
        # parameter names for username and password used by the login endpoint.
        # No clue why they do this. Maybe "for security reasons".
        #
        # They also use some tokens. Some are mandatory to avoid 500.
        # Some, not sure...
        logging.debug("loading session variables...")

        self.session = requests.Session()
        s = self.session
        r = s.get(
            BASE_URL,
            allow_redirects=True,
            verify=not self.debug,  # don't validate certificate if debug mode
        )

        # Get next url which is emdebed in an iframe
        # We must get this url which include some values we need
        soup = bs4.BeautifulSoup(r.text, 'html.parser')
        iframes = soup.find_all('iframe')
        url = BASE_URL + iframes[0].attrs['src']

        # Get some params. Not sure which are mandatory or even variable
        r = s.get(
            url
        )
        self.login_params = {
            # These two seem fixed and seem not to make a difference
            # 'sessiontoken': '5abcfd042b26eb423ae0ebda84f8505',
            # 'P2hoCyPjpg': 'bGFuZ3VhZ2U6ZW4tR0IsY29sb3JEZXB0aDoyNCxkZXZpY2VNZW1vcnk6bm90IGF2YWlsYWJsZSxzY3JlZW5SZXNvbHV0aW9uOjkwMCwxNDQwLGF2YWlsYWJsZVNjcmVlblJlc29sdXRpb246ODM3LDE0NDAsdGltZXpvbmVPZmZzZXQ6MCx0aW1lem9uZTpFdXJvcGUvTGlzYm9uLGNwdUNsYXNzOm5vdCBhdmFpbGFibGUscGxhdGZvcm06TWFjSW50ZWwsd2ViZ2xWZW5kb3JBbmRSZW5kZXJlcjpJbnRlbCBJbmMufkludGVsKFIpIElyaXMoVE0pIFBsdXMgR3JhcGhpY3MgNjQ1LHRvdWNoU3VwcG9ydDowLGZhbHNlLGZhbHNlLGF1ZGlvOjM1LjczODMyOTU5MzA5MjI%3D',  # noqa
            'accion': '3',
            'ssafe': '',
            'linkHomeURL': ''
        }

        # Get the param values from hidden inputs in the page html
        soup = bs4.BeautifulSoup(r.text, 'html.parser')
        items = soup.find_all('input')
        for item in items:
            if item.attrs['name'] in self.login_params and 'value' in item.attrs:  # noqa
                self.login_params[item.attrs['name']] = item.attrs['value']

        # Not sure if this call is necessary...
        r = s.get(
            BASE_URL + "nbp_guard"
        )

        # Now this seems required to get the CSRF token that will be
        # used later on
        headers = {
            'FETCH-CSRF-TOKEN': '1',
        }
        r = s.post(
            BASE_URL + "nbp_guard",
            headers=headers,
        )
        self.OGC_TOKEN = r.text.split(':')[1]  # the token!

        # This timestamp seems irrelevant but we'll keep it as is
        ts = str(time.time()).split('.')[0]
        r = s.get(
            BASE_URL + "jsp/sanpt/usuarios/login_functions.jsp?_=" + ts,
            headers={
                'OGC_TOKEN': self.OGC_TOKEN,  # must have this token in
            }
        )

        # Now this next call will return a script which includes the
        # obfuscated parameter names.

        # Here's the timestamp again
        ts = str(time.time()).split('.')[0]
        r = s.get(
            BASE_URL + "jsp/sanpt/usuarios/loginForm_novo.jsp?_=" + ts,
            headers={
                'OGC_TOKEN': self.OGC_TOKEN,  # must have the token
            }
        )

        # Finding username and password obfuscated parameter names
        # from the returned script. The values are repeated a few times
        # in the code. The first time is the password.
        matches = re.findall(
            "\'([A-Z0-9]+)\'",
            r.text,
        )
        self.password_param_name = matches[0]  # first occurrence
        for match in matches:
            if match != self.password_param_name:
                self.username_param_name = match
                break
        return

    def is_authenticated(self):
        raise NotImplementedError

    def authenticate(self, user, password):
        """ Actual authentication. Needs variables previously loaded """
        logging.debug("authenticating...")

        self.login_params[self.username_param_name] = user
        self.login_params[self.password_param_name] = password
        self.login_params['OGC_TOKEN'] = self.OGC_TOKEN
        s = self.session
        s.post(
            url=BASE_URL + LOGIN_PAGE,
            data=self.login_params,
            headers={
                "Origin": BASE_URL,
                "Connection": "close",
            }
        )
        # TODO: check if login successful

        # getting next legit url from embedded redirect script
        # not sure if we really need this
        # matches = re.findall(
        #     "\'(.+)\'",
        #     r.text,
        # )
        # url = matches[0]

    def get_account_list(self):
        raise NotImplementedError

    def get_account(self, number=0):
        logging.debug("getting account")
        return SantanderAccount(number, self)

    def get_card_list(self):
        s = self.session
        r = s.post(
            url=GETCARDS_URL,
            data={
                'OGC_TOKEN': self.OGC_TOKEN,
            }
        )
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        debit_cards = []
        credit_cards = []
        table = soup.find('table', attrs={'class': 'trans', 'id': 'Table5'})

        lines = table.find_all('tr')
        for line in lines:
            if 'class' in line.attrs and 'total' in line.attrs['class']:
                break
            if 'class' in line.attrs and 'header' in line.attrs['class']:
                continue
            if 'class' in line.attrs and 'sectn' in line.attrs['class']:
                if 'Débito' in line.text:
                    cards = debit_cards
                elif 'Crédito' in line.text:
                    cards = credit_cards
                continue
            columns = line.find_all('td')
            card_id = columns[0].find('input').attrs['value']
            card_name = columns[0].find('a').text.strip()
            cards.append({
                'id': card_id,
                'name': card_name,
            })
        return (debit_cards, credit_cards)

    def get_card(self, card_id):
        logging.debug("getting card")
        return SantanderCard(card_id, self)


class SantanderAccount(Account):
    def __init__(self, number, bank):
        self.number = number
        self.bank = bank

    def get_movements(self, iter_pages=False, since_date=None):
        s = self.bank.session
        next_page = 0
        transactions = []
        while True:
            params = {
                "OGC_TOKEN": self.bank.OGC_TOKEN,
            }
            if next_page > 0:
                params['numeroPagina'] = str(next_page)
            r = s.post(
                url=GETTRANSACTIONS_URL,
                data=params
            )
            soup = bs4.BeautifulSoup(r.text, "html.parser")

            items = soup.find_all('a', attrs={"class": "tr"})
            for item in items:
                columns = item.find_all('span')
                for col in columns:
                    if 'DataValor' in col.attrs['id']:
                        valuedate = col.text
                    elif 'DataOperacao' in col.attrs['id']:
                        date = col.text
                    elif 'Descricao' in col.attrs['id']:
                        description = col.text
                    elif 'Valor' in col.attrs['id']:
                        value = col.text
                    elif 'Saldo' in col.attrs['id']:
                        balance = col.text # noqa
                transaction = SantanderTransaction(
                    date,
                    valuedate,
                    description,
                    value,
                )
                if (
                    since_date is None or
                    transaction.date > since_date or
                    transaction.value_date > since_date
                ):
                    transactions.append(transaction)
            if not iter_pages:
                break
            current_page = int(soup.find_all('li', attrs={'class': 'current'})[0].text)
            next_page = 0
            for li in soup.find_all('li'):
                if 'class' in li.attrs and 'current' in li.attrs['class']:
                    current_page = int(li.text)
                elif 'onclick' in li.attrs and 'cambioPagina' in li.attrs['onclick']:
                    if 'class' not in li.attrs:
                        if int(li.text) > current_page:
                            next_page = int(li.text)
                            break
            if next_page == 0:
                break
        return transactions


class SantanderCard():

    def __init__(self, id, bank):
        self.bank = bank
        self.id = id

    def get_card_statement_list(self):
        s = self.bank.session
        r = s.post(
            url=GETCARD_STATEMENTS_URL,
            data={
                'accion': '2',
                'codigoTarjeta': self.id,
                'numMovements': '15',
                'idProduct': '',
                'tipoTarjeta': '',
                'cardId': self.id,
                'OGC_TOKEN': self.bank.OGC_TOKEN,
            }
        )
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        table = soup.find('table', attrs={'id': 'Table5', 'class': 'trans'})
        lines = table.find_all('tr')
        statements = []
        for line in lines:
            if 'header' in line.attrs['class']:
                continue
            columns = line.find_all('td')
            if len(columns) != 3:
                continue

            statement_id = columns[0].text
            sdate = columns[1].text.strip()
            if sdate != '':
                statement_date = SantanderTransaction.parse_date(sdate)
            else:
                statement_date = None
            statement_state = columns[2].text.strip()
            statements.append(
                {
                    'id': statement_id,
                    'date': statement_date,
                    'state': statement_state,
                }
            )
        return statements

    def get_movements(self, statement_id, iter_pages=False, since_date=None):
        s = self.bank.session
        transactions = []
        page_number = ''
        while True:
            r = s.post(
                url=GETCARD_TRANSACTIONS_URL,
                data={
                    'accion': '3',
                    'params': 'si',
                    'numeroPagina': page_number,
                    'codigoTarjeta': self.id,
                    'codigoExtracto': statement_id, 
                    'cardId': self.id,
                    'extractId': statement_id,
                    'OGC_TOKEN': self.bank.OGC_TOKEN,
                }
            )
            soup = bs4.BeautifulSoup(r.text, "html.parser")
            table = soup.find('table', attrs={'class': 'trans'})
            lines = table.find_all('tr')
            if len(lines) == 0:
                return []

            for line in lines:
                if 'class' in line.attrs and 'header' in line.attrs['class']:
                    continue
                columns = line.find_all('td')
                date = columns[0].text.strip()
                description = columns[1].text.strip()
                cred_or_deb = columns[3].text.strip()
                value = columns[4].text.strip()
                if 'Débito' in cred_or_deb:
                    value = "-" + value
                transaction = SantanderTransaction(
                    date, date, description, value)
                if (
                    since_date is None or
                    transaction.date > since_date or
                    transaction.value_date > since_date
                ):
                    transactions.append(transaction)
            if not iter_pages:
                break
            page_number = ''
            pages = soup.find('p', attrs={'class': 'pages'})
            current_page = pages.find('strong').text
            other_pages = pages.find_all('a')
            for other_page in other_pages:
                if '>>' in other_page.text:
                    page_number = re.findall(
                        "cambioPagina\(\'(\d+)\'",
                        other_page.attrs['href'],
                    )[0]
                    continue
            if page_number == '':
                break
        return transactions


class SantanderTransaction(Transaction):
    
    def parse_value(self, value):
        try:
            # we're expecting Santander value format like 'mmm.ccc,dd EUR'
            # we remove "." characters and then replace "," by "."
            # to convert to float
            valid_value = value.replace('.', '').replace(',', '.').replace(' EUR', '')
            return float(valid_value)
        except ValueError:
            return None

    @staticmethod
    def parse_date(value):
        try:
            # we're expecting Santander date format like this 'dd-mm-yyyy'
            # validating and creating a real date object
            valid_date = datetime.strptime(value, '%d-%m-%Y')
            return date(valid_date.year, valid_date.month, valid_date.day)
        except ValueError:
            return None
