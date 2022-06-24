from cloud_governance.common.logger.init_logger import logger
from cloud_governance.tag_non_cluster.remove_non_cluster_tags import RemoveNonClusterTags
from cloud_governance.tag_non_cluster.tag_non_cluster_resources import TagNonClusterResources
from cloud_governance.tag_non_cluster.update_na_tag_resources import UpdateNATags


def tag_non_cluster_resource(mandatory_tags: dict, region: str, tag_operation: str = 'read'):
    if tag_operation == 'update':
        action = 'Tag'
        dry_run = 'no'
    else:
        action = 'Scan'
        dry_run = 'yes'

    tag_non_cluster_resources = TagNonClusterResources(input_tags=mandatory_tags, region=region, dry_run=dry_run)

    func_resource_list = [tag_non_cluster_resources.non_cluster_update_ec2,
                          tag_non_cluster_resources.update_volumes,
                          tag_non_cluster_resources.update_ami,
                          tag_non_cluster_resources.update_snapshots,
                          ]
    logger.info(f"{action} {len(func_resource_list)} non-cluster resources  in region {region}:")
    for func in func_resource_list:
        func()


def remove_tag_non_cluster_resource(mandatory_tags: dict, region: str, dry_run: str = 'yes'):
    remove_tag_non_cluster_resources = RemoveNonClusterTags(input_tags=mandatory_tags, region=region, dry_run=dry_run)

    func_resource_list = [remove_tag_non_cluster_resources.non_cluster_update_ec2,
                          remove_tag_non_cluster_resources.update_volumes,
                          remove_tag_non_cluster_resources.update_ami,
                          remove_tag_non_cluster_resources.update_snapshots,
                          ]
    if dry_run == "no":
        action = 'Tag'
    else:
        action = 'Scan'
    logger.info(f"{action} {len(func_resource_list)} non-cluster resources  in region {region}:")
    for func in func_resource_list:
        func()


def tag_na_resources(file_name: str, file_path: str = '/tmp/', tag_operation: str = 'read', region: str = 'us-east-2'):
    """
    This method generate the NA tag file and update tags of each region
    @param file_path:
    @param tag_operation:
    @param region:
    @param file_name:
    @return:
    """
    file_name = f'{file_path}{file_name}'
    update_na_tags = UpdateNATags(region=region, file_name=file_name)
    if tag_operation == 'read':
        logger.info('Generating the CSV file')
        update_na_tags.create_csv()
    elif tag_operation == 'update':
        update_na_tags.update_tags()

