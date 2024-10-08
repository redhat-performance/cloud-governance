class PolicyResponse:

    def __init__(self, deleted, **kwargs):
        self.deleted = deleted
        self.message = "running on dry_run=True mode, no resource will get harm"
        self.error = "No Error"
        for key, value in kwargs.items():
            setattr(self, key, value)

    def set_value(self, key, value):
        setattr(self, key, value)
