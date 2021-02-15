#!/bin/bash

AWS_ACCESS_KEY_ID=$1
AWS_SECRET_ACCESS_KEY=$2
BUCKET=$3
ES_HOST=$4
ES_PORT=9200

echo "Upload data to ElasticSearch - ec2 index"
es_index='cloud-governance-ec2'
declare -a regions=('us-east-1' 'us-east-2' 'us-west-1' 'us-west-2')
declare -a policies=('ec2_idle' 'ec2_untag' 'ec2_run')
for region in "${regions[@]}"
do
   for policy in "${policies[@]}"
   do
       sudo podman run --rm --name cloud-governance -e upload_data_es='upload_data_es' -e es_host=$ES_HOST -e es_port=$ES_PORT -e es_index=$es_index -e bucket=$BUCKET -e policy=$policy -e AWS_DEFAULT_REGION=$region -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e log_level=INFO quay.io/ebattat/cloud-governance

   done
done

echo "Upload data to ElasticSearch - ebs index"
es_index='cloud-governance-ebs'
declare -a regions=('us-east-1' 'us-east-2' 'us-west-1' 'us-west-2')
declare -a policies=('ebs_unattached')
for region in "${regions[@]}"
do
   for policy in "${policies[@]}"
   do
       sudo podman run --rm --name cloud-governance -e upload_data_es='upload_data_es' -e es_host=$ES_HOST -e es_port=$ES_PORT -e es_index=$es_index -e bucket=$BUCKET -e policy=$policy -e AWS_DEFAULT_REGION=$region -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e log_level=INFO quay.io/ebattat/cloud-governance
   done
done