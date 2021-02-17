#!/bin/bash

AWS_ACCESS_KEY_ID=$1
AWS_SECRET_ACCESS_KEY=$2
BUCKET=$3
GIT_ACCESS_TOKEN=$4

echo "Run all policies pre active region"
declare -a regions=('us-east-1' 'us-east-2' 'us-west-1' 'us-west-2')
declare -a policies=('ec2_idle' 'ec2_untag' 'ec2_run' 'ebs_unattached')

for region in "${regions[@]}"
do
   for policy in "${policies[@]}"
   do
       sudo podman run --rm --name cloud-governance -e policy=$policy -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=$region -e dry_run=yes -e policy_output=s3://$BUCKET/logs/$region -e log_level=INFO quay.io/ebattat/cloud-governance
   done
done

echo "run gitleaks"
sudo podman run --rm --name cloud-governance -e policy=gitleaks -e git_access_token=$GIT_ACCESS_TOKEN -e git_repo=https://github.com/redhat-performance -e several_repos=yes -e log_level=INFO quay.io/ebattat/cloud-governance
