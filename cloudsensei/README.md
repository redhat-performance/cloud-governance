## CloudSensei

CloudSensei is a slack bot integrated with cloud governance, 
allowing users to join a “read-only” slack channel to review 
daily expense reports for instances (in running state) >= 7 days.
We have had a few occurrences where cloud resources were 
running indefinitely even after deleting the cluster. 
But these few occurrences are good enough to be proactive and 
this is where “CloudSensei” can give us quick access.

### How it works?
To implement this functionality, CloudSensei utilizes AWS Lambda + EventBridge.
The EventBridge Scheduler (CronJob) will run on every day 17:00hrs IST. 


#### How to send Slack notifications on Slack?
1. Create a new Slack bot on your slack workspace, add it to desired channel
2. Generate [OAuth](https://api.slack.com/authentication/token-types#bot) Token for Slack Bot
3. Use [Block Kit](https://api.slack.com/block-kit) to build message formats.
4. Use Slack [postMessage API](https://api.slack.com/methods/chat.postMessage) to post messages to Slack channel

#### Steps to create Slack bot:
1. Go to [api.slack.com](https://api.slack.com/)
2. Click on **Your apps** and click on **Manage your apps**.
3. Click on **Create New App**.
4. Select create from scratch.
   1. Enter necessary fields and create app
5. A Basic information tab will open, select options **Bots**.
6. Click on **OAuth & Permissions** on left panel
   1. Click on 
   2. Under the scopes, add only **Bots Token Scopes**
   3. Under the **OAuth Tokens for Your Workspace**, Submit **Install to Workspace** and allow access.

#### Adding Slack bot to your channel

To Create a Lambda function & integrate with EventBridge you must export some env variables:

Fill the env.txt file to export environment variables

To store the data of long-running instances in elastic search
export below variables
```commandline
ACCOUNT_ID=$<ACCOUNT_ID>
AWS_DEFAULT_REGION=$<AWS_DEFAULT_REGION>
RESOURCE_DAYS=$<RESOURCE_DAYS>
SEND_AGG_MAIL=$<SEND_AGG_MAIL>
ES_SERVER=$<ES_SERVER>
```

To send mail of the long-running instances
export below variables
```commandline
ACCOUNT_ID=$<ACCOUNT_ID>
AWS_DEFAULT_REGION=$<AWS_DEFAULT_REGION>
RESOURCE_DAYS=$<RESOURCE_DAYS>
SES_HOST_ADDRESS=$<SES_HOST_ADDRESS>
SES_HOST_PORT=$<SES_HOST_PORT>
SES_USER_ID=$<SES_USER_ID>
SES_PASSWORD=$<SES_PASSWORD>
TO_ADDRESS=$<TO_ADDRESS>
CC_ADDRESS=$<CC_ADDRESS>
```

To send Slack notifications in Slack channel
export below variables
```commandline
ACCOUNT_ID=$<ACCOUNT_ID>
AWS_DEFAULT_REGION=$<AWS_DEFAULT_REGION>
RESOURCE_DAYS=$<RESOURCE_DAYS>
SLACK_API_TOKEN=$<SLACK_API_TOKEN>
SLACK_CHANNEL_NAME=$<SLACK_API_TOKEN>
```

Note: Use env.txt to export above varibales

```commandline
git clone https://github.com/redhat-performance/cloud-governance
cd cloud-governance/cloudsensei/
./run.sh deploy
# Copy the tfstate file backup, incase it is deleted, we cannot retrieve it
```

To delete the Lambda + Event_bridge service [ ** must have the tfstate file]
```commandline
cd cloudsensei
./run.sh destroy
```

##### Limits of BlockKit

1. Can only send 50 item per block.
