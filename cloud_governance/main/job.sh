declare -a regions=('us-east-1' 'us-east-2' 'us-west-1' 'us-west-2')
declare -a policies=('ec2_idle' 'ebs_unattached' 'ec2_untag')
# 1. Run all policies pre active region
for region in "${regions[@]}"
do
   for policy in "${policies[@]}"
   do
       sudo podman run --rm --name cloud-governance -e policy=$policy -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=$region -e dry_run=yes -e policy_output=${{ secrets.PACKAGE_NAME }}/logs/$region -e log_level=INFO quay.io/ebattat/cloud-governance
   done
done
# 2. Upload data to ElasticSearch
sudo podman run --rm --name cloud-governance -e upload_data_elk='upload_data_elk' -e es_host='localhost' -e es_port='9200' -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e log_level=INFO quay.io/ebattat/cloud-governance