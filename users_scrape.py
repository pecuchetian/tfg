#!/home/pecuchet/UOC/tfg-venv/bin/python
import threading
import queue
from queries import user, db
import logging
import sys
from time import sleep

logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format="%(threadName)s : %(message)s"
                   )

log = logging.getLogger(__name__)



def scrape_user(url, round):
    u  = user.User(url, round=round)
    #u.self.mastodon_fetch_friends(fwing_or_fwers)
    #u.mastodon_fetch_friends('following')
    
    #server is not dead
    u.get_friends()
    fwingcount_db = u.get_user_degree('following')
    fwerscount_db = u.get_user_degree('followers')
    u.set_round()
    u.db.close()
    # if fwingcount_db >= u.followers_count and fwerscount_db >= u.followers_count:
    #     
    return u

class SetQueue(queue.Queue):
    def _init(self, maxsize):
        self.queue = set()
    def _put(self, item):
        self.queue.add(item)
    def _get(self):
        return self.queue.pop()

def worker(q, lock, currently_scraping, round):
    while True:
        item = q.get()
        netloc = user.User._get_server(item)
        with lock:
            if netloc in currently_scraping:
                q.task_done()
                q.put(item)
                continue
            else:
                currently_scraping.add(netloc)
        log.info('Working on %s', item)
        scrape_user(item, round)
        log.info('Finished %s', item)
        q.task_done()
        with lock:
            currently_scraping.remove(netloc)
        
def supervisor(q, db, currently_scraping, lock, round):
    while True:
        
        if q.qsize() < 100:
            remaining = populateq(q, db, round)
            with lock:
                log.info("Supervisor here. Size of queue: %s: .  Number of threads: %s. Active search: %s", q.qsize(), threading.active_count(), currently_scraping)
            if remaining == 0:
                return
        sleep(10)            
            
def populateq(q, db, round):
    db = db.Db()
    usrs = db.get_unscraped_nodes(round)
    db.close()
    for usr in usrs:
        q.put(usr)
    log.info("We put %s nodes in the queue." , len(usrs))
    return len(usrs)

round = 1

q = SetQueue()

lock = threading.Lock()
currently_scraping = set()

for i in range(10):
    threading.Thread(target=worker, args=(q, lock, currently_scraping, round)).start()

threading.Thread(target=supervisor, args=(q, db, currently_scraping, lock, round)).start()

q.join()