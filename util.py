class HttpClient:

    def __init__(self, session):
        self.session = session

    def download(self, url, timeout=None, headers={}, verify_ssl=True):
        response = self.session.get(url, timeout=timeout, headers=headers)
        return response.text, response.url
