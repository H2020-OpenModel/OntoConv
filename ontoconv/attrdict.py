"""Dict with attribute access."""


class AttrDict(dict):
    """Simple implementation of a dict with attribute access.

    Use with care. Methods like `keys()` can be overwritten by
    incoming data.

    Code from:
    https://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self
