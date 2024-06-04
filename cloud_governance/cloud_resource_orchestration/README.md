## Cloud Resource Orchestration

This is the process to control costs on public clouds. \
This process requires the data how many days a project will run and estimated_cost. \
Details are collected from the front end page @[https://cloud-governance.rdu2.scalelab.redhat.com/](https://cloud-governance.rdu2.scalelab.redhat.com/)
After filling the form, mail sent to manager for approval after approved your request.
Tag your instances with TicketId: #ticket_number. \
Then cloud_governance will start **cloud_resource_orchestration** and monitor your instances.

To start **cloud_resource_orchestration** CI run the below podman command

```commandline
podman run --net="host" --rm --name  cloud_resource_orchestration -e AWS_DEFAULT_REGION="ap-south-1" -e CLOUD_RESOURCE_ORCHESTRATION="True" -e account="$account" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e PUBLIC_CLOUD_NAME="$PUBLIC_CLOUD_NAME" -e es_host="$ES_HOST" -e es_port="$ES_PORT" -e CRO_ES_INDEX="$CRO_ES_INDEX" -e log_level="INFO" -e LDAP_HOST_NAME="$LDAP_HOST_NAME" -e JIRA_QUEUE="$JIRA_QUEUE" -e JIRA_TOKEN="$JIRA_TOKEN" -e JIRA_USERNAME="$JIRA_USERNAME" -e JIRA_URL="$JIRA_URL" -e CRO_COST_OVER_USAGE="$CRO_COST_OVER_USAGE" -e CRO_PORTAL="$CRO_PORTAL" -e CRO_DEFAULT_ADMINS="$CRO_DEFAULT_ADMINS" -e CRO_REPLACED_USERNAMES="$CRO_REPLACED_USERNAMES" -e CRO_DURATION_DAYS="30" quay.io/ebattat/cloud-governance:latest
```
