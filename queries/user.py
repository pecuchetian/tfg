from urllib.parse import (urlparse, urlsplit, urljoin, urlunsplit,  urlunparse)
import requests, json, pprint, time, warnings
import logging
from mastodon import Mastodon
from mastodon.errors import MastodonNotFoundError, MastodonVersionError
from queries import db, server


log = logging.getLogger(__name__)
waiting_time = 30
pp = pprint.PrettyPrinter(indent=3)

class User():
    
    webfinger = "/.well-known/webfinger?resource="
    
    def __init__(self, handle, round):
        self.handle = handle
        self.round = round
        self.name = None
        self.uri = None
        self.server = None
        self.mastodon = None
        self.revert_to_mastodon_api = False
        self.db = db.Db()
        self.following_url = None
        self.followers_url = None
        self.followers = None
        self.following = None
        self.followers_count = None
        self.following_count = None        
        try:
            self.set_user_url()
            self.db.add_user(self)
        except (requests.exceptions.ConnectionError, json.JSONDecodeError) as e:
            log.warn(e)
            self.server = self.user_to_server(self.handle)
            self.db.set_dead_server(self.server, self.round)
            self.uri = self.handle
            self.db.add_user(self)

        try:
            self.set_linked_nodes_urls()
        except (KeyError, json.JSONDecodeError, requests.exceptions.ConnectionError) as e:
            log.warning(e)
            # now try mastodon API
            self.revert_to_mastodon_api = True
            
    
    def set_linked_nodes_urls(self):
        """Get AP endpoints for followers and following related to user."""
        headers ={'accept' : 'application/activity+json'}
        r = requests.request(method='GET', url=self.uri, headers=headers)
        d = json.loads(r.text)
        #log.info('User endpoint reply: %s', pprint.pformat(d))
        log.debug('Following endpoint: %s', d['followers'])
        self.following_url = d['following']
        self.followers_url = d['followers']


    def set_user_url(self):
        log.debug("Parsing this: %s", type(self.handle))
        parsed = urlsplit(self.handle)
        # maybe check wether server is in db
        # print(parsed)
        log.debug("Parsed this: %s", parsed)
        
        homeurl = urlunsplit((parsed[0], parsed[1], '', '',  ''))
        
        resource = parsed.path
        
        headers ={'accept' : 'application/activity+json'}
        
        # url = homeurl  + webfinger + resource
        url = urljoin(homeurl + self.webfinger, resource)
        
        log.debug("Will request info at %s", url)
        r = requests.request(method='GET', url=url, headers=headers)
        if r.status_code != 200:
            log.warn('%s non 200 reply: %s', url, r.status_code)
            
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
        self.uri = self.handle
        try:      
            self.name = rdict['name']
        except:
            log.warn("WHOLE USER AP INFO %s", rdict)  
        self.server = homeurl

    def get_linked_nodes(self, collection_url):
        headers ={'accept' : 'application/activity+json'}
        r = requests.request(method='GET', url=collection_url, headers=headers)
        collection = []
        if r.status_code == 200:
            d = json.loads(r.text)
            log.debug('Collection reply: %s', d)
            
            splits = collection_url.split('/')
            fwing_or_fwers = splits[-1]
            degree = self.get_user_degree(fwing_or_fwers)
            
            log.debug('%s in db %s: %s\nIn object: %s,\n In request: %s',
                     self.uri,
                     fwing_or_fwers,
                     degree,
                     getattr(self, fwing_or_fwers + "_count"),
                     d.get('totalItems')
                    )
            
            # check that all is well
            if int(d['totalItems']) > 0 and d.get('first')  and degree < int(d['totalItems']):
                log.debug("%s total items: %s", self.uri, d['totalItems'])
                self.update_follow_count(int(d['totalItems']), fwing_or_fwers)
                next = d.get('first')
                # pleroma complains
                if (type(next) == dict):
                    next = next.get('id')
                while next:
                    r = requests.request(method='GET', url= next, headers=headers)
                    log.debug('%s status code:  %s', self.uri, r.status_code)

                    if r.status_code == 200:
                        f = json.loads(r.text)
                        log.debug('Fetching %s',next)
                        next =  f.get('next')
                        # remove this as it is a waste of memory
                        #collection += f['orderedItems']
                        self.save_to_db(f['orderedItems'], fwing_or_fwers)
                    elif r.status_code == 429:
                        log.warning('TOO MANY REQUESTS. SLEEPING FOR A MINUTE: %s', next)
                        time.sleep(60)
                        # self.mastodon_fetch_friends(fwing_or_fwers)
                    else:
                        log.error("ABORTING user %s at %s: Status:%s", self.uri, fwing_or_fwers, r.status_code)
                        raise requests.RequestException("WE GOT A STRANGE RESPONSE")
            
            else:
                warnings.warn("SKIPPING DOWNLOAD")                
        else:
            warnings.warn("SKIPPING DOWNLOAD: GOT A NON 200 RESPONSE")
            self.db.set_dead_user(self.uri, self.round)
        return collection

    def get_friends(self):
        
        if  self.is_mastodon():
            self.mastodon_fetch_friends('followers')
            self.mastodon_fetch_friends('following')            

        else:
            self.followers = self.get_linked_nodes(self.followers_url)
            self.following = self.get_linked_nodes(self.following_url)

    
    def is_mastodon(self):
        s = server.Server(self.server)
        if s.soft == 'mastodon':
            return True
        else:
            return False
            
    def to_mastodon_user(self):
        parsed = urlparse(self.uri)
        #print(parsed)
        usr = parsed.path.split('/')[2]
        return usr + '@' + parsed.netloc
        
    def from_mastodon_user(self, uri):
        parsed = urlparse(uri)
        #log.info('%s', uri)
        usr = parsed.path.replace('@','users/')
        #log.info('%s', urlunparse(parsed._replace(path= usr)))
        return urlunparse(parsed._replace(path= usr))
        
    def mastodon_fetch_friends(self, fwers_or_fwing):
        usr = self.to_mastodon_user()
        log.info("MASTODON API: %s", usr)
        self.start_mastodon()
        try:
            mastopyuser = self.mastodon.account_lookup(usr)
            
        except (MastodonNotFoundError, MastodonVersionError) as e:
            log.warn(e)
            log.warn('Marking user as UNREACHABLE')
            self.db.set_dead_user(self.uri, self.round)
            return

        if fwers_or_fwing == 'following':
            f = self.mastodon.account_following(mastopyuser['id'])
        else:# let's assume it's followers
            f = self.mastodon.account_followers(mastopyuser['id'])        
        
        #print(self.from_mastodon_user(f[0]['url']))
        batch_of_people = [self.from_mastodon_user(u['url']) for u in f]
        setattr(self,
                fwers_or_fwing,
                batch_of_people)
        self.save_to_db(batch_of_people, fwers_or_fwing)
        #log.info('api response: %s', f)
        while f:
            f = self.mastodon.fetch_next(f)
            # log.debug('\n\nnew batch: %s', pprint.pformat(f))
            cur_fwers = getattr(self, fwers_or_fwing)
            if f:
                batch_of_people = [self.from_mastodon_user(u['url']) for u in f]
                cur_fwers +=  batch_of_people
                setattr(self, fwers_or_fwing, cur_fwers)
                self.save_to_db(batch_of_people, fwers_or_fwing)
            log.info('%s %s length so far: %s', self.uri, fwers_or_fwing, len(cur_fwers))
        

                     
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
        
    def set_round(self):
        self.db.set_user_round(self.uri, self.round)
        
    @staticmethod
    def _get_server(uri):
        parsed = urlparse(uri)
        return parsed.netloc
