#!/usr/bin/python3

import argparse
import requests
import json
import time
import datetime
import os
# from urllib import parse
from requests.models import PreparedRequest

class d3exc(Exception):
    pass

class D3():
    def __init__(self):
        self.user = None
        self.password = None
        self.sid = None
        self.uid = None
        self.headers = dict()
    
    def session_init(self, sid, uid):
            self.uid = int(uid)
            self.sid = sid

            self.headers = {
                'X-Futuware-UID': str(self.uid),
                'X-Futuware-SID': self.sid,
            }

    def auth(self, user=None, password=None):
        self.user=user
        self.password=password
        data = {
            'username': self.user,
            'password': self.password
        }

        r = requests.post('https://d3.ru/api/auth/login/', data=data)
        
        if r.status_code == 200:                
            data = r.json()
            self.session_init(sid = data['sid'], uid=data['uid'])
        else:
            print("auth code:", r.status_code, r.text)
            raise d3exc(f'{r.status_code} {r.text}')

    def vote(self, post_id, vote):
        url = f'https://d3.ru/api/posts/{post_id}/vote/'
        data = {'vote': vote}
        self.authrequest('POST', url, data)

    def last_posts(self, period, url=None, params=None, user=None):
        if url is None and params is None:
            if user:
                url = f'https://d3.ru/api/users/{user}/posts/'
                params = {}
            else:
                url = 'https://d3.ru/api/posts/'
                params = {'sorting': 'date_created'}

        page=1
        
        while True:
            reported=0
            req = PreparedRequest()
            params['page'] = page
            req.prepare_url(url, params)
            # print(req.url)

            r = requests.get(req.url)
            data = r.json()
            for pdata in data['posts']:
                try:
                    p = Post(pdata, client=self)
                except:
                    print("Failed to create posts structure")
                    print("DATA:", json.dumps(data, indent=4))
                    print("code:", r.status_code)
                    print("text:", r.text)
                    print("r:", r)

                if p.age() < period:
                    reported += 1
                    yield p
            
            if not reported:
                # print(f'// nothing found on page {page} size {len(data["posts"])}')
                return 
            else:
                # print(f'// page {page} size {len(data["posts"])} reported {reported}')
                page += 1

    def __repr__(self):
        return f'sid: {self.sid} uid: {self.uid}'

    def authrequest(self, method, url, data=None):
        if method == 'GET':
            r = requests.get(url, headers = self.headers)
        elif method == 'POST':
            r = requests.post(url, headers=self.headers, data=data)
        else:
            raise d3exc(f'unknown method {method}')

        if r.status_code != 200:
            raise d3exc(f'{method} {url} {r.status_code} {r.text}')
        return r

    def me(self):
        r = self.authrequest('GET','https://d3.ru/api/my')
        return r.json()

class Comment():
    def __init__(self, post, data):
        self.data = data
        self.user = data['user']['login']
        self.uid = data['user']['id']
        self.body = data['body']
        self.post = post

    def __repr__(self):
        return f'{self.post.id} {self.user}: {self.body}'


class Post():
    def __init__(self, data=None, post_id=None, client=None):

        self.client = client 

        if post_id:
            url = f'https://d3.ru/api/posts/{post_id}/'

            if client:
                r = client.authrequest('GET', url)
            else:
                r = requests.get(url)            
                if r.status_code != 200:
                    raise d3exc(f'GET {url} {r.status_code} {r.text}')
            data = r.json()

        self.data = data
        self.id = data['id']
        self.username = data['user']['login']
        self.title = data['data']['title']
        self.domain = data['domain']['url']
        self.rating = data['rating'] or 0
        self.created = data['created']
        self.karma = data['user']['karma']

    

    def __repr__(self):
        return f'#{self.id:<10} ({self.age():7}s ago) {self.rating:4} {self.domain:30}{self.username:20}({self.karma}) {self.title}'

    def age(self):
        return int(time.time() - self.created)

    def dump(self):
        return json.dumps(self.data, indent=4)

    def vote(self, vote):
        self.client.vote(self.id, vote)

    def get_comments(self):
        r = requests.get(f'https://d3.ru/api/posts/{self.id}/comments/')
        for c in r.json()['comments']:
            yield Comment(post=self, data=c)

    def comment(self, body):
        url = f'https://d3.ru/api/posts/{self.id}/comments/'
        data = {'body': body}
        return self.client.authrequest('POST', url, data)

    def unpublish(self):
        r = self.client.authrequest('POST',f'https://d3.ru/api/posts/{self.id}/unpublish/')

    def getattr(self, name):
        return self.data[name]

    def can_unpublish(self):
        return self.getattr('can_unpublish')
        

Posts = [Post]



def get_args():
    parser = argparse.ArgumentParser(description = 'd3 antispam checked')
    parser.add_argument('--size', type=int, default=20, help='page size (number of posts in page)')
    parser.add_argument('--period', default='1h', help='period (e.g. 12h or 2d)')

    group = parser.add_argument_group('Authentication')
    group.add_argument('--user', '-u', help='your username', default = os.getenv('D3USER'))
    group.add_argument('--password', '-p', help='your password', default=os.getenv('D3PASS'))

    group = parser.add_argument_group('Authentication (debug)')
    group.add_argument('--uid', help='uid', default = os.getenv('D3UID'))
    group.add_argument('--sid', help='session id', default=os.getenv('D3SID'))

    group = parser.add_argument_group('Spam criterion')
    group.add_argument('--posts', type=int, default=10, help='>= N posts during --period')
    group.add_argument('--neg', type=int, default=5, help='>= N posts with negative rating during --period')

    group = parser.add_argument_group('Spam reaction')
    group.add_argument('--body', default=None, help='specify body to comment each punished post')
    group.add_argument('--minus', default=False, action='store_true', help='Vote (-1) for spam post')
    group.add_argument('--unpublish', default=False, action='store_true', help='Unpublish post (if possible)')

    return parser.parse_args()

def get_posts(period: int) -> Posts:
    sorting = 'date_created'
    page = 1
    stop = False

    while not stop:
        reported = 0

        url = f'https://d3.ru/api/posts/?page={page}&sorting={sorting}'
        r = requests.get(url)
        data = r.json()
        for pdata in data['posts']:
            p = Post(pdata)
            if p.age() < period:
                reported += 1
                yield p
        
        if not reported:
            print(f'// nothing found on page {page} size {len(data["posts"])}')
            return 
        else:
            print(f'// page {page} size {len(data["posts"])} reported {reported}')
            page += 1


def is_spammer(d3: D3, user: str, period: int, posts: int, neg: int):
    print(f'checking user {user}...')

    page=1
    user_karma = 0

    calc_posts = 0
    calc_neg = 0

    for post in d3.last_posts(period=period, user=user):
        print(post)
        user_karma = post.karma
        if post.age() < period:
            calc_posts += 1
            if post.rating < 0:
                calc_neg += 1

    if calc_posts >= posts and calc_neg >= neg:
        print(f'User {user} ({user_karma}) is spammer. {calc_posts} posts ({calc_neg} negative) in {period} seconds')
        return True
    return False

def punish(d3: D3, user: str, body: str, minus: bool, unpublish: bool, period: int):
    for post in d3.last_posts(period=period, user=user):
            print("PUNISH", post)
            # VOTE
            if minus:
                try:                
                    post.vote(-1)
                except d3exc as e:
                    pass

            if body:
                commented = False
                # COMMENTED? (unreliable!)
                for comment in post.get_comments():
                    if comment.uid == d3.uid:
                        commented = True
                        break
                                            
                if not commented:
                    try:
                        post.comment(body)
                    except d3exc as e:
                        pass
                        # print("comment failed:", e)
            
            if unpublish:
                print(f'unpublish #{post.id}')
                post.unpublish()

# main
def main():
    args = get_args()

    users = list()

    if args.period[-1]=='d':
        period = int(args.period[:-1])*86400
    elif args.period[-1]=='h':
        period = int(args.period[:-1])*3600
    elif args.period[-1]=='s':
        period = int(args.period[:-1])
    else:
        period = int(args.period)


    d3 = D3()
    if args.uid and args.sid:        
        d3.session_init(sid=args.sid, uid=args.uid)
    else:
        d3.auth(args.user, args.password)
        print(d3)

    me = d3.me()
    print(f"Working as user: {me['login']} #{me['id']}")

    print("Started:", datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'))
    started = time.time()

    for post in d3.last_posts(period=period):
        # print(post)
        if post.rating<0:
            if not post.username in users:
                users.append(post.username)

    for user in users:
        if is_spammer(d3, user, period=period, posts=args.posts, neg=args.neg):
            punish(d3, user, 
                body=args.body,
                minus=args.minus,
                unpublish=args.unpublish, 
                period=period)
            return

    print(f'Finished in {int(time.time() - started)} seconds')

main()