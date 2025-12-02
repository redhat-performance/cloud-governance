Contributing to cloud-governance
=====================

## How to Contribute
The cloud-governance project welcomes contributions from everyone!  Please read the below steps to see how you can contribute.

## Environment Setup

- Before going further we assume you must have the python3 installed in your system.

- Clone `main` branch for latest, or a specific release branch

```
git clone --single-branch --branch main https://github.com/redhat-performance/cloud-governance.git
```
- Change directory to the code and create your own branch to work

```
cd cloud-governance/
git checkout -b <name_of_change>
python3.14 -m venv .venv
source ./.venv/bin/activate
pip install -r requirmenets.txt
```

## Adding the New Policies

- Choose the policy type by cloud in [policy](cloud_governance/policy) folder.
- Choose the policy type that need to be created. \
If the policy is cleanup/ idle choose cleanup folder.
- You will find the common methods that will be useful for tracking in [helper](cloud_governance/common/helpers) folder by cloud.

### Policy Directory Structure

- main
  - aws_main_operations.py
  - main.py
- common
  - helper
    - aws
      - aws_cleanup_operations.py
    - azure
      - azure_cleanup_operations.py
    - cleanup_operations.py
    - Json_datetime_encoder.py
- policy
  - aws
      - cleanup
        - ec2_run
          - ebs_use
        - tagging
        - cost_reports
  - policy_runners
    - aws
      - policy_runner.py
      - upload_s3.py
    - azure
      - policy_runner.py
    - elasticsearch
      - upload_elasticsearch.py
    - common
      - abstract_policy_runner.py
      - abstract_upload.py

###  Rules to implement Policies

- Each policy needs to be run in two modes dry_run=yes/ no.
- RUN_ACTIVE_REGIONS=True env variable runs the policy in all active regions and the data will be uploaded to the ElasticSearch and s3/ storage bucket.
  This is already implemented in [policy_runner](cloud_governance/policy/policy_runners/aws/policy_runner.py).
- The S3 upload data format is key/region_name/policy/YYYY/MM/DD structure.
- Each policy will have the option to skip the action by having the resource tag **Policy=notdelete** or **skip=not_delete**.
- Each policy will have the env #DAYS_TO_TAKE_ACTION variable, which will take action that equals the days of DaysCount.
- Each policy has the alert days, which will be #DAYS_TO_TAKE_ACTION - 4 and alert the user if we configured the policy alert. ( Note: Currently this is disabled due to that we have the aggregated message policy )
- Possibilities for checking the dry_run days.
  - If an instance is Using/ stopped then set DaysCount=0
  - If an instance is running increment the counter based on dry_run=no mode by +1 else set 0
  - If dry_run == "no":
    - CountDays=date@#1
  - else:
    - If dry_run == "yes":
      - CountDays=date@#0
