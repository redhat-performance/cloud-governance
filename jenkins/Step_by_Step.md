# How to create a new user for cloud-governance
1. Create a IAM policy CloudGovernanceDeletePolicy
   1. Use [CloudGovernanceDeletePolicy.json](iam/clouds/aws/CloudGovernanceDeletePolicy.json) to create the policy
2. Create **cloud-governance-user** and add the above created policy.
3. Create s3 bucket to store policy results.

# Adding jenkins slave
1. Install java-11-jdk
    ```commandline
    sudo yum install java-11-openjdk-devel
    ```
2. Install docker on [Fedora](https://docs.docker.com/engine/install/fedora/)
   ```commandline
    sudo dnf -y install dnf-plugins-core
    sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
    sudo dnf install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-compose
    sudo systemctl start docker
    ```
3. Create Jenkins user
   ```commandline
    useradd jenkins -U -s /bin/bash
   passwd jenkins
    ```
4. Add jenkins user to sudoers file
    ```
   $ vi /etc/sudoers
   jenkins ALL=(ALL) NOPASSWD: ALL
   ```
5. Giving permissions to jenkins user to run docker container
    ```
   sudo chown jenkins:jenkins /var/run/docker.sock
    ```

6. Run the cloud_governance_stack [ ElasticSearch, Kibana, Grafana]
    ```commandline
    # using docker-compose.yml
    # detached mode
    docker-compose -f [docker_compose_file_path](jenkins/docker-compose.yml) up -d
    # down the containers
    docker-compose -f [docker_compose_file_path](jenkins/docker-compose.yml) down
    ```

# Connect Jenkins slave to master
1. Goto Jenkins master.
2. Click on **Manage Jenkins**
3. CLick on **Manager Nodes and Clouds**
4. Click on New Node
5. Add details like node **Name**
6. Configure Node
   1. Remote root directory: **/home/jenkins**
   2. LaunchMethod: Launch agents via ssh
      1. Host: **hostname**
      2. Credentials: *select you creds from drop down*
         1. ADD CREDS: select kind as Username with password
      3. Host key Verification Strategy: _Non verifying Verification Strategy_
      4. Click on Advanced:
         1. Port: 22/
         2. JavaPath: /usr/bin/java
7. Click on save.
8. Check logs, if slave is connected to master or not.

##  How to add AWS Creds to jenkins master.
1. Create a JSON file with below format and save it. [ Keep it safe ]
    ```commandline
    {
    "account1": {
       "AWS_ACCESS_KEY_ID": "acces_key",
       "AWS_SECRET_ACCESS_KEY" : "acees_secret",
       "BUCKET" : "bucket_name"
     },
    "account2": {
       "AWS_ACCESS_KEY_ID": "acces_key",
       "AWS_SECRET_ACCESS_KEY" : "acees_secret",
       "BUCKET" : "bucket_name"
     }
    }
    ```
2. Login into the jenkins console.
3. Click on Manager Jenkins
4. Select Manage Credentials
5. Click on **System**, select the domain that your creds will be stored
   1. Add Credentials.
      1. Select **secret file**
      2. Give the Id
      3. Upload the json file
   2. Update Credentials
      1. Select the secret you want to upgrade.
      2. If it is a file secret.
      3. Upload the modified file.