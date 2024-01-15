#!/home/pecuchet/UOC/tfg-venv/bin/python
from mastodon import Mastodon
from mastodon.errors import MastodonNotFoundError, MastodonVersionError
from queries import db, server
from dotenv import load_dotenv
import os
import logging, sys

logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format="%(threadName)s : %(message)s"
                   )

log = logging.getLogger(__name__)

metrics_file = 'metrics/centrality.txt'

if __name__ == '__main__':
    # load secrets
    load_dotenv()
    token = os.getenv("BOTTOKEN")
    server = os.getenv("MASTOURL")
    #start mastodon
    
    mastodon = Mastodon(api_base_url=server,
                        access_token=token)
    # mydb = db.Db()
    # cent = mydb.get_deg_centrality()
    numbers = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
    txt = """Most central nodes in the Fediverse as seen by this bot:
Number {} is {} with {:,} followers.
    """
    log.info('Reading metrics file')
    with open(metrics_file) as f:
        lines = f.readlines()
        
        stat = txt.format(1,lines[0].split(',')[0],
                          int(lines[0].split(',')[1]))
        #print(stat)
        t = mastodon.status_post(stat)
        for i, l in enumerate(lines[1:]):
            stat = txt.format(i+2,
                              l.split(',')[0],
                              int(l.split(',')[1]))
            t = mastodon.status_reply(t, stat)

    log.info("Posted %s  toots.", i+2)
    



    
