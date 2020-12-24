# from cloud_governance.tag_cluster.run_tag_cluster_resouces import scan_cluster_resource, tag_cluster_resource
# from cloud_governance.zombie_cluster.run_zombie_cluster_resources import zombie_cluster_resource, delete_zombie_cluster_resource
# from time import gmtime, strftime
#
#
# def main():
#     region = 'us-east-2'
#     # scan cluster resources
#     cluster_name = 'ocs-test-jlhpd'
#     scan_cluster_resource(cluster_name=cluster_name, region=region)
#
#     # cluster resources tag
#     # input tags
#     mandatory_tags = {
#         "Name": "test-opc464",
#         "Owner": "Eli Battat",
#         "Email": "ebattat@redhat.com",
#         "Purpose": "test",
#         "Date": strftime("%Y/%m/%d %H:%M:%S")
#     }
#     tag_cluster_resource(cluster_name=cluster_name, mandatory_tags=mandatory_tags, region=region)
#
#     # zombie cluster resource
#     zombie_cluster_resource(delete=False, region=region)
#     #delete_zombie_cluster_resource(delete=True, region=region)
#
# main()
