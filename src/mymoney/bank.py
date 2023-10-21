import urllib.request


class Bank:
    def __init__(
        self, info, proxy=None, debug=False,
        ignore_ssl_verication=False,
        persist_cookies=False,
    ):
        self.info = info
        self.debug = debug
        self.add_proxy(proxy)
        # only supported for BPI at this time
        self.ignore_ssl_verication = ignore_ssl_verication
        self.login(persist_cookies=persist_cookies)

    def login(self):
        pass

    def get_account_list(self):
        pass

    def search_movement(self, *kwargs):
        pass

    def add_proxy(self, proxy):  # TODO: maybe this should be moved somewhere
        if proxy:
            # TODO: support other kinds of proxies?
            self.proxy = urllib.request.ProxyHandler({'https': proxy})
        else:
            self.proxy = None
