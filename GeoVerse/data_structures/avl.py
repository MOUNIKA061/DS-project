class AVLNode:
    def __init__(self, key, value):
        self.key = key
        self.values = [value]
        self.left = None
        self.right = None
        self.height = 1

class AVLTree:
    """An AVL tree indexing timestamps -> list of DLLNode references.
    Supports insertion and range search.
    """
    def __init__(self):
        self.root = None

    def _height(self, node):
        return node.height if node else 0

    def _balance_factor(self, node):
        return self._height(node.left) - self._height(node.right)

    def _rotate_right(self, y):
        x = y.left
        T2 = x.right
        x.right = y
        y.left = T2
        y.height = 1 + max(self._height(y.left), self._height(y.right))
        x.height = 1 + max(self._height(x.left), self._height(x.right))
        return x

    def _rotate_left(self, x):
        y = x.right
        T2 = y.left
        y.left = x
        x.right = T2
        x.height = 1 + max(self._height(x.left), self._height(x.right))
        y.height = 1 + max(self._height(y.left), self._height(y.right))
        return y

    def _insert(self, node, key, value):
        if not node:
            return AVLNode(key, value)
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            node.values.append(value)
            return node

        node.height = 1 + max(self._height(node.left), self._height(node.right))
        balance = self._balance_factor(node)

        # LL
        if balance > 1 and key < node.left.key:
            return self._rotate_right(node)
        # RR
        if balance < -1 and key > node.right.key:
            return self._rotate_left(node)
        # LR
        if balance > 1 and key > node.left.key:
            node.left = self._rotate_left(node.left)
            return self._rotate_right(node)
        # RL
        if balance < -1 and key < node.right.key:
            node.right = self._rotate_right(node.right)
            return self._rotate_left(node)

        return node

    def insert(self, key, value):
        self.root = self._insert(self.root, float(key), value)

    def _range_collect(self, node, start, end, out):
        if not node:
            return
        if node.key > start:
            self._range_collect(node.left, start, end, out)
        if start <= node.key <= end:
            out.extend(node.values)
        if node.key < end:
            self._range_collect(node.right, start, end, out)

    def search_range(self, start, end):
        out = []
        self._range_collect(self.root, float(start), float(end), out)
        return out

    def to_list(self):
        out = []
        def inorder(n):
            if not n: return
            inorder(n.left)
            out.append((n.key, [v.to_dict() for v in n.values]))
            inorder(n.right)
        inorder(self.root)
        return out

    def find_nearest(self, key):
        """Find the node(s) with the timestamp nearest to `key`.
        Returns list of DLLNode values (could be multiple if exact match) or [] if tree empty.
        """
        if not self.root:
            return []
        key = float(key)
        node = self.root
        nearest = node
        while node:
            # update nearest if closer
            if abs(node.key - key) < abs(nearest.key - key):
                nearest = node
            # traverse
            if key < node.key:
                node = node.left
            elif key > node.key:
                node = node.right
            else:
                # exact match
                return list(node.values)
        return list(nearest.values)
