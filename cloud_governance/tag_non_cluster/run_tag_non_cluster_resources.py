from cloud_governance.common.logger.init_logger import logger
from cloud_governance.tag_non_cluster.tag_non_cluster_resources import TagNonClusterResources


def tag_non_cluster_resource(mandatory_tags: dict, region: str, dry_run: str):
    tag_non_cluster_resources = TagNonClusterResources(input_tags=mandatory_tags, region=region, dry_run=dry_run)

    func_resource_list = [tag_non_cluster_resources.non_cluster_update_ec2,
                          tag_non_cluster_resources.update_volumes,
                          tag_non_cluster_resources.update_ami,
                          tag_non_cluster_resources.update_snapshots,
                          ]
    if dry_run == "no":
        action = 'Tag'
    else:
        action = 'Scan'
    logger.info(f"{action} {len(func_resource_list)} cluster resources  in region {region}:")
    for func in func_resource_list:
        func()
