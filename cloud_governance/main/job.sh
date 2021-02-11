
# 1. Run all policies pre active region
declare -a regions=('us-east-1' 'us-east-2' 'us-west-1' 'us-west-2')
declare -a policies=('ec2_idle' 'ebs_unattached' 'ec2_untag')

for region in "${regions[@]}"
do
   for policy in "${policies[@]}"
   do
       sudo podman run --rm --name cloud-governance -e policy=$policy -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=$region -e dry_run=yes -e policy_output=s3://$bucket/logs/$region -e log_level=INFO quay.io/ebattat/cloud-governance
   done
done

# 2. Upload data to ElasticSearch - ec2 index
declare -a regions=('us-east-1' 'us-east-2' 'us-west-1' 'us-west-2')
declare -a policies=('ec2_idle' 'ec2_untag')
for region in "${regions[@]}"
do
   for policy in "${policies[@]}"
   do
       sudo podman run --rm --name cloud-governance -e upload_data_es='upload_data_es' -e es_host='elasticsearch.intlab.perf-infra.lab.eng.rdu2.redhat.com' -e es_port='9200' -e es_index='json_ec2_timestamp_index' -e bucket=$bucket -e policy=$policy -e region=$region -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e log_level=INFO quay.io/ebattat/cloud-governance

   done
done

# 3. Upload data to ElasticSearch - ebs index
declare -a regions=('us-east-1' 'us-east-2' 'us-west-1' 'us-west-2')
declare -a policies=('ebs_unattached')
for region in "${regions[@]}"
do
   for policy in "${policies[@]}"
   do
       sudo podman run --rm --name cloud-governance -e upload_data_es='upload_data_es' -e es_host='elasticsearch.intlab.perf-infra.lab.eng.rdu2.redhat.com' -e es_port='9200' -e es_index='json_ebs_timestamp_index' -e bucket=$bucket -e policy=$policy -e region=$region -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e log_level=INFO quay.io/ebattat/cloud-governance
   done
done
