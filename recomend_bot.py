#!/home/pecuchet/UOC/tfg-venv/bin/python
from mastodon import Mastodon
from mastodon.errors import MastodonNotFoundError, MastodonVersionError
from mastodon.streaming import CallbackStreamListener
from queries import db, server
from dotenv import load_dotenv
import os
import re
import pprint
import logging
from bs4 import BeautifulSoup

pp = pprint.PrettyPrinter(indent=3)
log = logging.getLogger(__name__)

# class Listener(mastodon.StreamListener):

#     def on_update(self, status):
#         print(f"on_update: {status}")
#         # on_update: {'id': 109371390226010302, 'content': '<p>Listening to Toots...</p>',
#         #  'account': {'id': 109359234895957150, 'username': 'admin'}, ...}

#     def on_notification(self, notification):
#         # print(f"on_notification: {notification}")
#         print(notification)
#         if '@botbot' in status.content:
#             usr_acc = re.search(r'users like ([^ ]+)')
#             reply_text = '@' + status.account.username + ' Hello there!\n'
#             if usr_acc:
#                 reply_text += "Let's try to find users similar to {}.".format(usr_acc.group(1))

#                 mastodon.status_post(reply_text)
#             # Follow notification:
#         # on_notification: {'id': 7, 'type': 'follow',
#         #  'account': {'id': 109370544417433130, 'username': 'some_friend'}, ...}

def get_similar_users(user_handle):
    usr_clean = user_handle.replace('@', 'users/')
    print("Getting users similar to {}".format(usr_clean))
    mydb = db.Db()
    sim_nodes = mydb.get_similar_nodes(usr_clean)
    print(sim_nodes)
    return sim_nodes

def handle_mention(notification):
    # pprint.pprint (status)
    try:
        status = notification.status
        soup = BeautifulSoup(status.content, "html.parser")
        usrs = soup.find_all('a')
        
        if status.content.find('users like') and usrs[1].get('href'):
            
            reply_text =  'Hello there!\n'
            reply_text += "Let's try to find users similar to {}.".format(usrs[1].get('href'))

            similar_users = get_similar_users(usrs[1].get('href'))
            reply_text += "\n\nWhat about this ones?: "

            mastodon.status_post(reply_text, in_reply_to_id=status.id)
            for usr, score in similar_users:
                txt = "This user has similarity score {:.2} with {}\n\n{}"
                mastodon.status_post(
                    txt.format(score, usrs[1].get_text(), usr),
                    in_reply_to_id=status.id)

        else:
            mastodon.status_post(
                "Please, if you want me to suggest similar users, please direct message me with text 'users like ' + a fediverse user address.",
                in_reply_to_id=status.id)

           


    except (KeyError, IndexError) as e:
        log.warning(e)
        print(e)
        mastodon.status_post("Not sure what happened, but I couldn't fulfill your request.\nMention me and add 'users like +fedi_user_account' to receive similar users.", in_reply_to_id=status.id)

if __name__ == '__main__':
    # load secrets
    load_dotenv()
    token = os.getenv("BOTTOKEN")
    server = os.getenv("MASTOURL")
    
    #start mastodon
    mastodon = Mastodon(api_base_url=server,
                        access_token=token)
    # Start streaming for mentions
    listener = CallbackStreamListener(notification_handler = handle_mention)
    mastodon.stream_user(listener)
