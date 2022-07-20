from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_non_cluster.zombie_non_cluster_resources import ZombieNonClusterResources


def zombie_non_cluster_resource(region: str = 'us-east-2', dry_run: str = 'yes'):
    """
    @param region:
    @param resource:
    @param resource_name:
    @param dry_run:
    @return:
    """
    zombie_non_cluster = ZombieNonClusterResources(region=region, dry_run=dry_run)
    zombie_resources = [
                        zombie_non_cluster.zombie_snapshots,
                        zombie_non_cluster.zombie_elastic_ip
                        ]
    for func in zombie_resources:
        response = func()
        logger.info(f'Key: {func.__name__} length: {len(response)} values: {response}')
