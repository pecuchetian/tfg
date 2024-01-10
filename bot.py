#!/home/pecuchet/UOC/tfg-venv/bin/python
from mastodon import Mastodon
from mastodon.errors import MastodonNotFoundError, MastodonVersionError
from queries import db, server
from dotenv import load_dotenv
import os


if __name__ == '__main__':
    # load secrets
    load_dotenv()
    token = os.getenv("BOTTOKEN")
    server = os.getenv("MASTOURL")
    #start mastodon
    
    mastodon = Mastodon(api_base_url=server,
                        access_token=token)
    mydb = db.Db()
    cent = mydb.get_deg_centrality()

    txt = """Most central nodes in the Fediverse as seen by this bot:


    """
    for c,s in cent:
        txt += """
{}: {}""".format(c, int(s))
    
    mastodon.toot(txt)
    


    
