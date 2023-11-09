from urllib.parse import (urlparse, urlsplit, urljoin, urlunsplit)
import requests, json, pprint, time, warnings
import logging
from mastodon import Mastodon
from queries import db


log = logging.getLogger(__name__)


class User():
    
    webfinger = "/.well-known/webfinger?resource="
    
    def __init__(self, handle):
        self.handle = handle 
        self.name = None
        self.uri = None
        self.server = None
        self.mastodon = None
        self.db = db.Db()
        
        self.set_user_url()
        self.db.add_user(self)
        
        self.following_url = None
        self.followers_url = None
        self.followers = None
        self.following = None
        self.followers_count = None
        self.following_count = None
        # wrap in try_except?
        self.set_linked_nodes_urls()


    
    def set_linked_nodes_urls(self):
        
        """Get AP endpoints for followers and following related to user."""
        headers ={'accept' : 'application/activity+json'}
        r = requests.request(method='GET', url=self.uri, headers=headers)
        d = json.loads(r.text)
        
        #log.info('User endpoint reply: %s', pprint.pformat(d))
        #log.info('Following endpoint: %s', d['following'])
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
        #pprint.pprint(rdict)
        user_AP = url
        user_AP = rdict.get('id')
        if rdict.get('links') != None:

            for  d in rdict['links']:
                if d['rel'] == 'self' and d['type'] == 'application/activity+json':
                    user_AP = d['href']
                    break
        log.debug("Settling with this user endpoint: %s", user_AP)        
        self.uri = user_AP
        self.name = rdict['name']
        self.server = homeurl

    def get_linked_nodes(self, collection_url):
        headers ={'accept' : 'application/activity+json'}
        r = requests.request(method='GET', url=collection_url, headers=headers)

        if r.status_code == 200:
            d = json.loads(r.text)
            log.debug('Collection reply: %s', d)
            collection = []
            splits = collection_url.split('/')
            fwing_or_fwers = splits[-1]
            degree = self.get_user_degree(fwing_or_fwers)
            
            log.info('In db %s: %s\nIn object: %s,\n In request: %s',
                     fwing_or_fwers,
                     degree,
                     getattr(self, fwing_or_fwers + "_count"),
                     d.get('totalItems')
                    )
            
            # check that all is well
            if int(d['totalItems']) > 0 and d.get('first')  and degree < int(d['totalItems']):
                log.info("Total items: %s", d['totalItems'])
                self.update_follow_count(int(d['totalItems']), fwing_or_fwers)
                next = d.get('first')
                # pleroma complains
                if (type(next) == dict):
                    next = next.get('id')
                while next:
                    r = requests.request(method='GET', url= next, headers=headers)
                    log.info('Status code:  %s', r.status_code)

                    if r.status_code == 200:
                        f = json.loads(r.text)
                        log.info('Fetching %s',next)
                        next =  f.get('next')
                        collection += f['orderedItems']
                        self.save_to_db(f['orderedItems'], fwing_or_fwers)
                    elif r.status_code == 429:
                        log.info('next: %s', next)
                        warnings.warn("TOO MANY REQUESTS. SLEEPING FOR A MINUTE.")
                        time.sleep(60)
                        # self.mastodon_fetch_friends(fwing_or_fwers)
                    else:
                        log.error("ABORTING: Status:%s", st)
                        raise requests.RequestException("WE GOT A STRANGE RESPONSE")
            
            else:
                warnings.warn("SKIPPING DOWNLOAD")                
        else:
            warnings.warn("SKIPPING DOWNLOAD: GOT A NON 200 RESPONSE")
        return collection

    def get_friends(self):
        #log.info('Followers endpoint: %s', self.followers_url)
        self.followers = self.get_linked_nodes(self.followers_url)
        self.following = self.get_linked_nodes(self.following_url)


    def to_mastodon_user(self):
        parsed = urlparse(self.uri)
        print(parsed)
        usr = parsed.path.split('/')[2]
        return usr + '@' + parsed.netloc
        print(parsed)
        
    def mastodon_fetch_friends(self, fwers_or_fwing):
        usr = self.to_mastodon_user()
        self.start_mastodon()
        mastopyuser = self.mastodon.account_lookup(usr)

        if fwers_or_fwing == 'following':
            f = self.mastodon.account_followers(mastopyuser['id'])
        else:# let's assume it's followers
            f = self.mastodon.account_followers(mastopyuser['id'])            
        
        setattr(self,
                fwers_or_fwing,
                [{'name' : u['username'],'uri' : u['uri'],'server' : u['uri']} for u in f])
        #log.info('api response: %s', f)
        while f:
            f = self.mastodon.fetch_next(f)
            # log.debug('\n\nnew batch: %s', pprint.pformat(f))
            cur_fwers = getattr(self, fwers_or_fwing)
            if f:
                cur_fwers +=  [{'name' : u['username'],
                               'uri' : u['uri'],
                               'server' : self.user_to_server(u['acct'])} for u in f]
                setattr(self, fwers_or_fwing, cur_fwers)
            log.info('F length so far: %s', len(cur_fwers))
        

                     
    def user_to_server(self, uri):
        parsed = urlsplit(uri)
        
        homeurl = urlunsplit((parsed[0], parsed[1], '', '',  ''))        
        return(homeurl)

    def start_mastodon(self):
        if not self.mastodon:
            mastodon = Mastodon(
                api_base_url=self.server)
            self.mastodon = mastodon

    def save_to_db(self, items, fwing_or_fwers):
        if fwing_or_fwers == 'following':
            self.db.add_following(self.uri, items)
        elif fwing_or_fwers == 'followers':
            self.db.add_followers(self.uri, items)
        self.db.close()

    def update_follow_count(self, count, fwing_or_fwers):
        setattr(self, fwing_or_fwers + "_count", count)
        self.db.update_follow_count(self.uri, count, fwing_or_fwers)
        
    def get_user_degree(self, fwing_or_fwers):
        if fwing_or_fwers == 'followers':
            degree = self.db.get_user_in_degree(self.uri)
        else:
            degree = self.db.get_user_out_degree(self.uri)
        degree_count = int(degree[0]['count'])        
        return degree_count

