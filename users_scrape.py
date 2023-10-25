#!/home/pecuchet/Yandex.Disk/UOC/TFG/tfg-venv/bin/python

from queries import user
import logging
import sys
import  pprint
from mastodon import Mastodon

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
log = logging.getLogger(__name__)

u  = user.User('https://mastodon.eugasser.com/@pecuchet')

# u.get_friends()

v = user.User('https://mastodon.social/users/Gargron')
# v.get_friends()
# pprint.pprint(v.following)
mastodon = Mastodon(
    api_base_url='https://mastodon.social'
)

v.mastodon_fetch_followers()
# mastouser = v.to_mastodon_user()
# log.debug('Mastouser:%s', mastouser)
# mastopyuser = mastodon.account_lookup(mastouser)
# f = mastodon.account_followers(mastopyuser['id'])
# #log.debug('first batch: %s', pprint.pformat(f))
# followers = [{'username' : u['username'],
#               'uri' : u['uri'],
#               'acct' : u['acct']} for u in f]

# while f:
#     f = mastodon.fetch_next(f)
#     # log.debug('\n\nnew batch: %s', pprint.pformat(f))
#     if f:

#         followers += [{'username' : u['username'],
#                        'uri' : u['uri'],
#                        'acct' : u['acct']} for u in f]
#     log.info('F length so far: %s', len(followers))



