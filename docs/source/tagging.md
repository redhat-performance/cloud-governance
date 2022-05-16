## How to auto tag your account?

This feature help you tagging your account for cluster, non cluster resource and IAM user.


1. Update all the users in account with permanent tags: [user_data_csv=read/write]<br>
   we create a simple way to read all user into csv, update tags in the csv by columns, and run podman to update it in IAM.
   1. read - generates csv file with all the users and tags of users. [ manually update the list ]
   2. update - Updates the tags of users in IAM

```sh
# policy=tag_iam_user
sudo podman run --rm --name cloud-governance -e policy=tag_iam_user -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e user_data_csv=read/update -v $PWD/user/tag_user.csv:/usr/local/cloud_governance/main/user/tag_user.csv -e log_level=INFO quay.io/ebattat/cloud-governance
```

2. Update all the resources Cluster/Non-Cluster by create user tags.<br>
   It will update all the non tags resource per region [Limit: only if the resource was created in the last 90 days].
   1. mandatory_tags: it adds the tags to the resource.
   
```sh
# policy=tag_resources
sudo podman run --rm --name cloud-governance -e policy=tag_resources -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=yes -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level=INFO -v /etc/localtime:/etc/localtime quay.io/ebattat/cloud-governance
```

3. Update all the non-cluster resources by create user tags and mandatory tags
    It will update all the non tags of non-cluster resource per region [Limit: only if the resource was created in the last 90 days].
   1. mandatory_tags: it adds the tags of the resource if it doesn't have any data on user.
   
```sh
# policy=tag_non_cluster
sudo podman run --rm --name cloud-governance -e policy=tag_non_cluster -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=yes -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level=INFO -v /etc/localtime:/etc/localtime quay.io/ebattat/cloud-governance
```



