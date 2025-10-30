import os
import json
import uuid
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from .dll import DoublyLinkedList
from .avl import AVLTree
from .queue_ds import QueueDS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STORAGE_FILE = os.path.join(ROOT, 'storage.json')

class UserStore:
    """Manages users and per-user data structures (in-memory).
    Persistence: basic JSON file to store user ids and password hashes. The data structures are kept in memory.
    """
    def __init__(self):
        self.users = {}        # userid -> {phone, password_hash}
        self.phone_map = {}    # phone -> userid
        self.structs = {}      # userid -> {dll, avl, queue}
        self._load()

    def _load(self):
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}
        else:
            data = {}
        self.users = data.get('users', {})
        self.phone_map = data.get('phone_map', {})
        # persisted timelines: userid -> [ {timestamp, lat, lon, source} ... ]
        self.timelines = data.get('timelines', {})
        # persisted offline queues: userid -> [ {timestamp, lat, lon, source:'offline'} ... ]
        self.queues = data.get('queues', {})

    def _save(self):
        data = {'users': self.users, 'phone_map': self.phone_map, 'timelines': getattr(self, 'timelines', {}), 'queues': getattr(self, 'queues', {})}
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def create_user(self, phone, password):
        if phone in self.phone_map:
            raise ValueError('Phone already registered')
        userid = str(uuid.uuid4())
        pw_hash = generate_password_hash(password)
        self.users[userid] = {'phone': phone, 'password_hash': pw_hash}
        self.phone_map[phone] = userid
        self._save()
        # initialize in-memory structures
        self.init_user_structures(userid)
        return userid

    def reserve_user(self, phone):
        """Reserve a userid for a phone number before password is set.
        This creates the phone->userid mapping and a user entry with empty password.
        """
        if phone in self.phone_map:
            raise ValueError('Phone already registered')
        userid = str(uuid.uuid4())
        # empty password_hash signifies pending creation
        self.users[userid] = {'phone': phone, 'password_hash': ''}
        self.phone_map[phone] = userid
        # initialize empty persisted timeline and queue
        if not hasattr(self, 'timelines'):
            self.timelines = {}
        if not hasattr(self, 'queues'):
            self.queues = {}
        self.timelines[userid] = []
        self.queues[userid] = []
        self._save()
        return userid

    def set_password_for_user(self, userid, password):
        """Set password for an already reserved userid and initialize user structures."""
        if userid not in self.users:
            raise ValueError('userid not found')
        pw_hash = generate_password_hash(password)
        self.users[userid]['password_hash'] = pw_hash
        self._save()
        # initialize in-memory structures
        self.init_user_structures(userid)
        return userid

    def authenticate(self, login, password):
        # login can be phone or userid
        userid = None
        if login in self.phone_map:
            userid = self.phone_map[login]
        elif login in self.users:
            userid = login
        else:
            return None
        pw_hash = self.users[userid]['password_hash']
        if check_password_hash(pw_hash, password):
            return userid
        return None

    def init_user_structures(self, userid):
        dll = DoublyLinkedList()
        avl = AVLTree()
        queue = QueueDS()

        # If we have a persisted timeline for this user, rebuild structures from it.
        persisted = getattr(self, 'timelines', {}).get(userid)
        if persisted and len(persisted) > 0:
            # ensure sorted by timestamp
            persisted = sorted(persisted, key=lambda x: x['timestamp'])
            for entry in persisted:
                node = dll.append(entry['timestamp'], entry.get('lat', 0.0), entry.get('lon', 0.0), source=entry.get('source', 'online'))
                avl.insert(entry['timestamp'], node)
        else:
            # Insert a current location as initial entry (timestamp now)
            import time
            now = time.time()
            initial_node = dll.append(now, 0.0, 0.0, source='online')
            avl.insert(now, initial_node)
            # persist initial timeline
            if not hasattr(self, 'timelines'):
                self.timelines = {}
            self.timelines[userid] = dll.to_list()
            self._save()

        # rebuild queue from persisted queues if available
        persisted_q = getattr(self, 'queues', {}).get(userid, [])
        for it in persisted_q:
            queue.enqueue(it)

        self.structs[userid] = {'dll': dll, 'avl': avl, 'queue': queue}
        return self.structs[userid]

    def get_structs(self, userid):
        if userid not in self.structs:
            return self.init_user_structures(userid)
        return self.structs[userid]

    def insert_location(self, userid, timestamp, lat, lon, online=True):
        s = self.get_structs(userid)
        if online:
            node = s['dll'].append(timestamp, lat, lon, source='online')
            s['avl'].insert(timestamp, node)
            # persist timeline
            if not hasattr(self, 'timelines'):
                self.timelines = {}
            self.timelines[userid] = s['dll'].to_list()
            self._save()
            return node
        else:
            # enqueue offline entry
            s['queue'].enqueue({'timestamp': float(timestamp), 'lat': float(lat), 'lon': float(lon), 'source': 'offline'})
            # persist queue
            if not hasattr(self, 'queues'):
                self.queues = {}
            # store as list of dicts
            self.queues[userid] = list(s['queue']._dq)
            self._save()
            return None

    def sync_queue(self, userid):
        s = self.get_structs(userid)
        items = s['queue'].get_all_and_clear()
        # sort items by timestamp and insert into dll and avl as 'synced'
        items.sort(key=lambda x: x['timestamp'])
        inserted = []
        for it in items:
            node = s['dll'].insert_sorted(it['timestamp'], it['lat'], it['lon'], source='synced')
            s['avl'].insert(it['timestamp'], node)
            inserted.append(node)
        # persist timeline and clear persisted queue
        if not hasattr(self, 'timelines'):
            self.timelines = {}
        self.timelines[userid] = s['dll'].to_list()
        if not hasattr(self, 'queues'):
            self.queues = {}
        self.queues[userid] = []
        self._save()
        return inserted

    def timeline(self, userid):
        s = self.get_structs(userid)
        return s['dll'].to_list()

    def search_range(self, userid, start_ts, end_ts):
        s = self.get_structs(userid)
        results = s['avl'].search_range(start_ts, end_ts)
        # results are DLLNode references; convert to dict
        return [r.to_dict() for r in results]

    def search_nearest(self, userid, ts):
        s = self.get_structs(userid)
        results = s['avl'].find_nearest(ts)
        return [r.to_dict() for r in results]

    def phone_to_userid(self, phone):
        return self.phone_map.get(phone)

    def userid_exists(self, userid):
        return userid in self.users
