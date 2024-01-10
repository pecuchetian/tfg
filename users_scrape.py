
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
    try:
        u  = user.User(url, round=round)
    except:
        log.warning('Could not create user instance %s', url)
        u.set_round()
        u.db.close()
    try:
        u.get_friends()
        #fwingcount_db = u.get_user_degree('following')
        #fwerscount_db = u.get_user_degree('followers')
    except:
        log.warning('Could not fetch friends %s', url)
        u.set_round()
        u.db.close()
    u.set_round()
    u.db.close()
    # if fwingcount_db >= u.followers_count and fwerscount_db >= u.followers_count:
    #     
    return u

def declare_user_unreacheable(item, db, round):
    db = db.Db()
    db.set_dead_user(item, round)
    db.close()

class SetQueue(queue.Queue):
    def _init(self, maxsize):
        self.queue = set()
    def _put(self, item):
        self.queue.add(item)
    def _get(self):
        return self.queue.pop()

def worker(q, lock, currently_scraping, db, round):
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
        try:
            scrape_user(item, round)
            log.info('Finished %s', item)
        except:
            declare_user_unreacheable(item, db, round)
            log.info('Failed %s. Declared unreacheable.', item)
        q.task_done()
        with lock:
            currently_scraping.remove(netloc)
        
def supervisor(q, db, currently_scraping, lock, round):
    while True:
        
        if q.qsize() < 500:
            remaining = populateq(q, db, round)
            with lock:
                log.info("Supervisor here. Size of queue: %s: .  Number of threads: %s. Active search: %s", q.qsize(), threading.active_count(), currently_scraping)
            if remaining == 0:
                return
        sleep(15)            
            
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


n_workers = 20
for i in range(n_workers):
    threading.Thread(target=worker, args=(q, lock, currently_scraping, db,  round)).start()

threading.Thread(target=supervisor, args=(q, db, currently_scraping, lock, round)).start()

q.join()

