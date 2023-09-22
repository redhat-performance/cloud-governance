from abc import ABC, abstractmethod

from cloud_governance.common.clouds.azure.compute.compute_operations import ComputeOperations
from cloud_governance.common.clouds.azure.compute.resource_group_operations import ResourceGroupOperations


class AbstractResource(ABC):

    def __init__(self):
        self._resource_group_operations = ResourceGroupOperations()
        self._compute_client = ComputeOperations()

    @abstractmethod
    def run(self):
        pass
