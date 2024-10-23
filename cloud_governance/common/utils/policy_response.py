from cloud_governance.main.environment_variables import environment_variables


class PolicyResponse:

    def __init__(self, deleted, **kwargs):
        self.deleted = deleted
        self.dry_run = environment_variables.dry_run
        self.message = "running on dry_run=True mode, no resource will get deleted"
        if self.dry_run == "no":
            self.message = "running on dry_run=False, resources will get deleted upon on days"
        self.error = "No Error"
        for key, value in kwargs.items():
            setattr(self, key, value)

    def set_value(self, key, value):
        setattr(self, key, value)
