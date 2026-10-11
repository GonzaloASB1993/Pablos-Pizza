"""Minimal in-memory Firestore fake for tests (never touches the real database)"""
import copy


class FakeDocSnapshot:
    def __init__(self, doc_id, data, reference=None):
        self.id = doc_id
        self._data = data
        self.reference = reference  # like google-cloud-firestore: lets callers delete/update the doc

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return copy.deepcopy(self._data) if self._data is not None else None


class FakeDocRef:
    def __init__(self, store, name, doc_id):
        self._store = store
        self._name = name
        self.id = doc_id

    def get(self, transaction=None):
        data = self._store.get(self._name, {}).get(self.id)
        return FakeDocSnapshot(self.id, data, reference=self)

    def set(self, data, merge=False):
        coll = self._store.setdefault(self._name, {})
        document = coll.setdefault(self.id, {}) if merge else {}
        for key, value in data.items():
            if type(value).__name__ == 'Increment':  # firestore.Increment(n) in set(merge=True): adds, creating the field
                document[key] = (document.get(key) or 0) + value.value
            else:
                document[key] = copy.deepcopy(value)
        coll[self.id] = document

    def update(self, data):
        coll = self._store.setdefault(self._name, {})
        if self.id not in coll:
            raise KeyError(f"No document to update: {self._name}/{self.id}")
        document = coll[self.id]
        for key, value in data.items():
            if type(value).__name__ == 'Increment':  # firestore.Increment(n): server-side add
                document[key] = (document.get(key) or 0) + value.value
            else:
                document[key] = copy.deepcopy(value)

    def delete(self):
        self._store.get(self._name, {}).pop(self.id, None)


class FakeQuery:
    _OPS = {
        '==': lambda a, b: a == b,
        '>=': lambda a, b: a is not None and a >= b,
        '<=': lambda a, b: a is not None and a <= b,
        '>': lambda a, b: a is not None and a > b,
        '<': lambda a, b: a is not None and a < b,
    }

    def __init__(self, store, name, filters=None, order=None, max_items=None):
        self._store = store
        self._name = name
        self._filters = filters or []
        self._order = order
        self._max = max_items

    def where(self, field, op, value):
        return FakeQuery(self._store, self._name, self._filters + [(field, op, value)], self._order, self._max)

    def order_by(self, field, direction='ASCENDING'):
        return FakeQuery(self._store, self._name, self._filters, (field, direction), self._max)

    def limit(self, n):
        return FakeQuery(self._store, self._name, self._filters, self._order, n)

    def stream(self):
        docs = [
            FakeDocSnapshot(doc_id, data, reference=FakeDocRef(self._store, self._name, doc_id))
            for doc_id, data in self._store.get(self._name, {}).items()
            if all(self._OPS[op](data.get(f), v) for f, op, v in self._filters)
        ]
        if self._order:
            field, direction = self._order
            docs.sort(key=lambda d: (d._data.get(field) is None, d._data.get(field)),
                      reverse=str(direction).upper().endswith('DESCENDING'))
        return iter(docs[:self._max] if self._max else docs)

    def get(self):
        return list(self.stream())


class FakeCollection(FakeQuery):
    def document(self, doc_id):
        return FakeDocRef(self._store, self._name, doc_id)


class FakeTransaction:
    """Applies writes immediately: enough to test logic, not real isolation"""

    def update(self, ref, data):
        ref.update(data)

    def set(self, ref, data, merge=False):
        ref.set(data, merge=merge)

    def delete(self, ref):
        ref.delete()


class FakeBatch:
    """Queues writes and applies them together on commit (all-or-nothing in the fake too)"""

    def __init__(self):
        self._ops = []

    def set(self, ref, data, merge=False):
        self._ops.append(lambda: ref.set(data, merge=merge))

    def update(self, ref, data):
        self._ops.append(lambda: ref.update(data))

    def delete(self, ref):
        self._ops.append(ref.delete)

    def commit(self):
        for op in self._ops:
            op()
        self._ops = []


class FakeFirestore:
    def __init__(self):
        self.store = {}

    def transaction(self):
        return FakeTransaction()

    def batch(self):
        return FakeBatch()

    def collection(self, name):
        return FakeCollection(self.store, name)
