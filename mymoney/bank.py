import urllib.request, urllib.error, urllib.parse

class Bank:
    def __init__(self, info,proxy=None):
        self.info = info
        self.add_proxy(proxy)
        self.login()

    def login(self):
        pass

    def get_account_list(self):
        pass

    def search_movement(self, *kwargs):
        pass

    def add_proxy(self,proxy): #TODO: maybe this should be moved somewhere else
        if proxy:
            self.proxy = urllib.request.ProxyHandler({'https': proxy}) #TODO: support other kinds of proxies?
        else:
            self.proxy = None
