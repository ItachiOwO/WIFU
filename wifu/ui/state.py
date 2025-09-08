from threading import Lock


class State(object):
    def __init__(self, state={}):
        self._state = state
        self._lock = Lock()
        self._listeners = {}
        self._changes = {}

    def add_element(self, key, elem):
        self._state[key] = elem
        self._changes[key] = True

    def has_element(self, key):
        return key in self._state

    def remove_element(self, key):
        del self._state[key]
        self._changes[key] = True

    def add_listener(self, key, cb):
        with self._lock:
            self._listeners[key] = cb

    def items(self):
        with self._lock:
            return self._state.items()

    def get(self, key):
        with self._lock:
            return self._state[key].value if key in self._state else None

    def reset(self):
        with self._lock:
            self._changes = {}

    def changes(self, ignore=()):
        with self._lock:
            changes = []
            for change in self._changes.keys():
                if change not in ignore:
                    changes.append(change)
            return changes

    def has_changes(self):
        with self._lock:
            return len(self._changes) > 0

    def set(self, key, value):
        with self._lock:
            if key in self._state:
                prev = self._state[key].value
                self._state[key].value = value

                if prev != value:
                    self._changes[key] = True
                    if key in self._listeners and self._listeners[key] is not None:
                        self._listeners[key](prev, value)
                        
    def next_page(self):
        """
        Move to the next page in the display
        """
        with self._lock:
            if 'pages' in self._state and 'current_page' in self._state:
                pages = self._state['pages'].value
                page = self._state['current_page'].value
                if page < len(pages) - 1:
                    self.set('current_page', page + 1)
                else:
                    self.set('current_page', 0)

    def prev_page(self):
        """
        Move to the previous page in the display
        """
        with self._lock:
            if 'pages' in self._state and 'current_page' in self._state:
                pages = self._state['pages'].value
                page = self._state['current_page'].value
                if page > 0:
                    self.set('current_page', page - 1)
                else:
                    self.set('current_page', len(pages) - 1)
