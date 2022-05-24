## How to auto tag your account?

This feature help you tagging your account for cluster, non cluster resource and IAM user.


1. Update all the users in account with permanent tags: [user_data_csv=read/write]<br>
   we create a simple way to read all user into csv, update tags in the csv by columns,delete the tags by specific keys and run podman to update it in IAM.
   1. read - generates csv file with all the users and tags of users. [ manually update the list ]
   2. update - Updates the tags of users in IAM
   3. delete - Delete the specific tags in IAM user

```sh
# policy=tag_iam_user
sudo podman run --rm --name cloud-governance -e policy=tag_iam_user -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e user_tag_operation=read/update/delete -e remove_tags="['Environment', 'Test']" -e username=test_username -e file_name=tag_user.csv  -e log_level=INFO -v /home/user/tag_user.csv:/tmp/tag_user.csv --privileged quay.io/ebattat/cloud-governance
```

2. Update all the resources Cluster/Non-Cluster by create user tags.<br>
   It will update all the non tags resource per region [Limit: only if the resource was created in the last 90 days].
   1. mandatory_tags: it adds the tags to the resource.
   2. tag_operation: read/update/delete to perform the operation
   
```sh
# policy=tag_resources
sudo podman run --rm --name cloud-governance -e policy=tag_resources -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e tag_operation=read/update/delete -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level=INFO -v /etc/localtime:/etc/localtime quay.io/ebattat/cloud-governance
```

3. Update all the non-cluster resources by create user tags and mandatory tags
    It will update all the non tags of non-cluster resource per region [Limit: only if the resource was created in the last 90 days].
   1. mandatory_tags: it adds the tags of the resource if it doesn't have any data on user.
   
```sh
# policy=tag_non_cluster
sudo podman run --rm --name cloud-governance -e policy=tag_non_cluster -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dtag_operation=read/delete/update -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level=INFO -v /etc/localtime:/etc/localtime quay.io/ebattat/cloud-governance
```



