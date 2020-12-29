from cloud_governance.tag_cluster.run_tag_cluster_resouces import scan_cluster_resource, tag_cluster_resource

region = 'us-east-1'
# scan cluster resources
cluster_name = 'ocs-test'
scan_cluster_resource(cluster_name=cluster_name, region=region)

