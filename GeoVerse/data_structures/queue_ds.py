from collections import deque

class QueueDS:
    def __init__(self):
        self._dq = deque()

    def enqueue(self, entry):
        self._dq.append(entry)

    def dequeue(self):
        return self._dq.popleft()

    def is_empty(self):
        return len(self._dq) == 0

    def get_all_and_clear(self):
        items = list(self._dq)
        self._dq.clear()
        return items

    def __len__(self):
        return len(self._dq)
