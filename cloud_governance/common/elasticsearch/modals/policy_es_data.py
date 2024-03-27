from datetime import datetime, timezone
from dataclasses import dataclass, asdict

from cloud_governance.common.utils.utils import Utils


@dataclass
class PolicyEsMetaData(dict):

    """
    This class is the data modal for policy elasticsearch data
    """

    account: str
    resource_id: str
    user: str
    skip_policy: str
    dry_run: str
    name: str
    region_name: str
    public_cloud: str
    expire_days: int

    unit_price: float = ''
    total_yearly_savings: float = ''
    resource_type: str = ''
    resource_state: str = ''
    clean_up_days: int = ''
    days_count: int = ''
    resource_action: str = ''
    IndexId: str = ''
    SnapshotDate: str = datetime.now(timezone.utc).date().__str__()

    # Specific Policy Attributes
    volume_size: int = ''
    instance_type: str = ''
    launch_time: str = ''
    running_days: int = ''
    create_date: str = ''

    def __post_init__(self):
        """
        This method initializes the IndexId
        :return:
        :rtype:
        """
        self.IndexId = (f'{self.SnapshotDate}-{self.public_cloud}-{self.account}-{self.region_name}-{self.resource_id}-'
                        f'{self.resource_state}').lower()

    def get_as_dict_title_case(self):
        """
        This method returns the dict object
        :return:
        :rtype:
        """
        return {Utils.convert_to_title_case(k): v for k, v in asdict(self).items() if v != ''}
