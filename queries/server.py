from urllib.parse import (urlparse, urlsplit, urljoin, urlunsplit,  urlunparse)
import requests, json, pprint, time, warnings
import logging

log = logging.getLogger(__name__)

pp = pprint.PrettyPrinter(indent=3)

class Server:

    endpoint = '/.well-known/nodeinfo'
    soft = ""
    

    def __init__(self, url) -> None:
        self.url = url
        try:
            self.node_info()
        except (JSONDecodeError, json.decoder.JSONDecodeError,Exception) as  e:
            log.warning('DEAD SERVER', e)
            self.soft = 'unknown'


    def node_info(self):
        r = requests.request(method='GET', url=self.url + self.endpoint)
        d = json.loads(r.text)
            
        r = requests.request(method='GET', url=d['links'][0]['href'])
        d = json.loads(r.text)
        self.soft = d['software']['name']
