from urllib.parse import (urlparse, urlsplit, urljoin, urlunsplit)
import requests, json, pprint
import logging
from mastodon import Mastodon

log = logging.getLogger(__name__)


class User():
    
    webfinger = "/.well-known/webfinger?resource="
    
    def __init__(self, handle):
        self.handle = handle 

        self.url = None
        self.server = None
        self.mastodon = None

        self.set_user_url()
        
        self.following_url = None
        self.followers_url = None
        self.followers = None
        self.following = None
        # wrap in try_except?
        self.set_linked_nodes_urls()

    
    def set_linked_nodes_urls(self):
        
        """Get AP endpoints for followers and following related to user."""
        headers ={'accept' : 'application/activity+json'}
        r = requests.request(method='GET', url=self.url, headers=headers)
        d = json.loads(r.text)

        #log.debug('User endpoint reply: %s', pprint.pformat(d))
        log.info('Following endpoint: %s', d['following'])
        self.following_url = d['following']
        self.followers_url = d['followers']

    def set_user_url(self):
        parsed = urlsplit(self.handle)
        # maybe check wether server is in db
        # print(parsed)
        log.debug("Parsed this: %s", parsed)
        
        homeurl = urlunsplit((parsed[0], parsed[1], '', '',  ''))
        
        resource = parsed.path
        
        headers ={'accept' : 'application/activity+json'}
        
        # url = homeurl  + webfinger + resource
        url = urljoin(homeurl + self.webfinger, resource)
        # print(url)
        log.debug("Will request info at %s", url)
        r = requests.request(method='GET', url=url, headers=headers)
        rdict = json.loads(r.text)
        pprint.pprint(rdict)
        user_AP = url
        user_AP = rdict.get('id')
        if rdict.get('links') != None:

            for  d in rdict['links']:
                if d['rel'] == 'self' and d['type'] == 'application/activity+json':
                    user_AP = d['href']
                    break
        log.debug("Settling with this user endpoint: %s", user_AP)        
        self.url = user_AP
        self.server = homeurl

    def get_linked_nodes(self, colletion_url):
        headers ={'accept' : 'application/activity+json'}
        r = requests.request(method='GET', url=colletion_url, headers=headers)
        log.info('Status code:  %s', r.status_code)
        if r.status_code == 200:
            d = json.loads(r.text)
            log.debug('Collection reply: %s', d)
            collection = []
            if int(d['totalItems']) > 0 and d.get('first'):
                next = d.get('first')
                # pleroma complains
                if (type(next) == dict):
                    next = next.get('id')
                while next:
                    
                    r = requests.request(method='GET', url= next, headers=headers)
                    log.info('Status code:  %s', r.status_code)
                    match r.status_code:
                        case 200:
                            f = json.loads(r.text)
                            log.info('Fetching %s',next)
                            next =  f.get('next')
                            collection += f['orderedItems']
                            self.savetodb()
                        case 429:
                            
                    elif 
        else:
            log.info(r)
        return collection

    def get_friends(self):
        log.info('Followers endpoint: %s', self.followers_url)
        self.followers = self.get_linked_nodes(self.followers_url)
        self.following = self.get_linked_nodes(self.following_url)


    def to_mastodon_user(self):
        parsed = urlparse(self.url)
        print(parsed)
        usr = parsed.path.split('/')[2]
        return usr + '@' + parsed.netloc
        print(parsed)
        
    def mastodon_fetch_followers(self):
        usr = self.to_mastodon_user()
        self.start_mastodon()
        mastopyuser = self.mastodon.account_lookup(usr)
        f = self.mastodon.account_followers(mastopyuser['id'])
        #log.debug('first batch: %s', pprint.pformat(f))
        #
        # RESOLVE PROBLEM WHEREAS eugasser.com does not
        # return uri key in collection and mastodon.social does
        #
        self.followers = [{'username' : u['username'],
                      'uri' : u['uri'],
                      'acct' : u['acct']} for u in f]

        while f:
            f = self.mastodon.fetch_next(f)
            # log.debug('\n\nnew batch: %s', pprint.pformat(f))
            if f:
                
                self.followers += [{'username' : u['username'],
                               'uri' : u['uri'],
                               'acct' : u['acct']} for u in f]
            log.info('F length so far: %s', len(self.followers))

       


    def start_mastodon(self):
        if not self.mastodon:
            mastodon = Mastodon(
                api_base_url=self.server)
            self.mastodon = mastodon

    def save_to_db(self):
        
        
