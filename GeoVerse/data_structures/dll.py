import time

class DLLNode:
    def __init__(self, timestamp, lat, lon, source="online"):
        self.timestamp = float(timestamp)
        self.lat = float(lat)
        self.lon = float(lon)
        self.source = source  # "online", "offline", "synced"
        self.prev = None
        self.next = None

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "lat": self.lat,
            "lon": self.lon,
            "source": self.source,
        }

class DoublyLinkedList:
    """A simple doubly linked list that maintains nodes in chronological order.
    Use insert_sorted for arbitrary timestamps (e.g. merging offline data).
    Append is optimized when timestamps are increasing (online flow).
    """
    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def append(self, timestamp, lat, lon, source="online"):
        node = DLLNode(timestamp, lat, lon, source)
        if not self.head:
            self.head = self.tail = node
        else:
            # common case: new timestamp >= tail.timestamp
            if node.timestamp >= self.tail.timestamp:
                self.tail.next = node
                node.prev = self.tail
                self.tail = node
            else:
                # fallback to sorted insert
                self.insert_sorted(node)
        self.size += 1
        return node

    def insert_sorted(self, node_or_timestamp, lat=None, lon=None, source="online"):
        """Insert a node preserving chronological order.
        Accept either a DLLNode or (timestamp, lat, lon, source).
        """
        if not isinstance(node_or_timestamp, DLLNode):
            node = DLLNode(node_or_timestamp, lat, lon, source)
        else:
            node = node_or_timestamp

        if not self.head:
            self.head = self.tail = node
            self.size = 1
            return node

        # fast path: append to tail
        if node.timestamp >= self.tail.timestamp:
            self.tail.next = node
            node.prev = self.tail
            self.tail = node
            self.size += 1
            return node

        # fast path: insert before head
        if node.timestamp <= self.head.timestamp:
            node.next = self.head
            self.head.prev = node
            self.head = node
            self.size += 1
            return node

        # otherwise scan from tail backwards or head forwards depending on closeness
        # choose direction by comparing to mid timestamp
        cur = self.tail
        while cur and cur.timestamp > node.timestamp:
            cur = cur.prev
        # now insert after cur
        nxt = cur.next
        cur.next = node
        node.prev = cur
        node.next = nxt
        if nxt:
            nxt.prev = node
        else:
            self.tail = node
        self.size += 1
        return node

    def to_list(self):
        out = []
        cur = self.head
        while cur:
            out.append(cur.to_dict())
            cur = cur.next
        return out

    def __len__(self):
        return self.size

    def clear(self):
        self.head = self.tail = None
        self.size = 0
