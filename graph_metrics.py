#!/home/pecuchet/UOC/tfg-venv/bin/python
from mastodon import Mastodon
from mastodon.errors import MastodonNotFoundError, MastodonVersionError
from queries import db, server
from dotenv import load_dotenv
import os, sys
import logging

logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format="%(threadName)s : %(message)s"
                   )

log = logging.getLogger(__name__)


if __name__ == '__main__':
    # load secrets
    load_dotenv()
    token = os.getenv("BOTTOKEN")
    server = os.getenv("MASTOURL")
    #start mastodon
    
    mastodon = Mastodon(api_base_url=server,
                        access_token=token)
    mydb = db.Db()
    
    # PROJECTION
    proj = mydb.project_users()
    log.info("Created projection %s", proj)

    # DEG CENTRALITY
    log.info("Getting degree centrality")
    cent = mydb.get_10_deg_cent()
    
    txt = ""
    for c,s in cent:
        txt += """{},{}
""".format(c, int(s))
    
    log.info("Writing centrality to file")
    with open('metrics/centrality.txt', 'w') as f:    
        f.write(txt)
        
    log.info("Getting graph stats")
    
    stats = mydb.graph_stats()
    
    for a,b,c,d in stats:
        txt += """{},{},{},{}
""".format(a,b,c,d)
    with open('metrics/stats.txt', 'w') as f:    
        f.write(txt)

    
#     # BETWEENNESS CENTRALITY
#     log.info("Getting betweenness centrality")
#     cent = mydb.get_10_between_cent()

#     txt = ""
#     for c,s in cent:
#         txt += """
# {}: {}""".format(c, int(s))
    
#     log.info("Writing betweennes centrality to file")
#     with open('metrics/betweenness.txt', 'w') as f:    
#         f.write(txt)    
    
    log.info("Dropping projection")
    mydb.drop_projection()
    log.info("Dropped projection %s")

    #mastodon.toot(txt)
    


    