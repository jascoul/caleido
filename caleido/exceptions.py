import sqlalchemy.exc

class StorageError(Exception):
    def __init__(self, *args, **kwargs):
        self.location = kwargs.pop('location', None)
        super(StorageError, self).__init__(*args, **kwargs)

    @classmethod
    def from_err(cls, err):
        if isinstance(err, sqlalchemy.exc.IntegrityError):
            return StorageError(err.args[0], location=None)

