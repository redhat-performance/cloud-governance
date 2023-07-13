PROJECT_NAME="CloudSensei"
SUCCESS_OUTPUT_PATH="/dev/null"
ERROR_LOG="$(mktemp -d)/stderr.log"

source ./env.sh


action="$1"

if [ -d "./terraform/.terraform" ]; then
  echo "Deleting the existing .terraform folder"
  rm -rf "./terraform/.terraform"
fi

if [ "$action" = "deploy"  ]; then
   echo "Clearing if previously created zip file"
    PROJECT_PATH="$PWD/$PROJECT_NAME.zip"
    if [ -f $PROJECT_PATH ]; then
        rm -rf  $PROJECT_PATH
        rm -rf ./package
        echo "Deleted Previously created zip file"
    fi

    pip install --upgrade pip
    pip install --target ./package -r ./requirements.txt > $SUCCESS_OUTPUT_PATH
    pushd ./package
    zip -r ../$PROJECT_NAME.zip . > $SUCCESS_OUTPUT_PATH
    popd
    zip -g $PROJECT_NAME.zip lambda_function.py > $SUCCESS_OUTPUT_PATH
    zip -g $PROJECT_NAME.zip email_template.j2 > $SUCCESS_OUTPUT_PATH
    zip -g $PROJECT_NAME.zip slack_operations.py > $SUCCESS_OUTPUT_PATH
    zip -g $PROJECT_NAME.zip es_operations.py > $SUCCESS_OUTPUT_PATH
    zip -g $PROJECT_NAME.zip send_email.py > $SUCCESS_OUTPUT_PATH

  pushd ./terraform
  echo "#############################"
  echo "Creating the lambda lambda_function using terraform"
  if [ -n "$ACCOUNT_ID" ]; then
    echo "Generating jinja files and tfvars file"
    python ./Template.py
    echo "Completed Generating tfvars file and jinja file"
    if command -v terraform; then
      if [ -s "$ERROR_LOG" ]; then
          rm -f "$ERROR_LOG"
          echo "Removed the stderr file if present"
      fi
      terraform init 1> $SUCCESS_OUTPUT_PATH
      terraform state pull
      terraform apply -var-file="./input_vars.tfvars" -auto-approve 2> "$ERROR_LOG"
      if [[ -s "$ERROR_LOG" ]]; then
        cat $ERROR_LOG
        terraform destroy -var-file="./input_vars.tfvars" -auto-approve
        echo "Validate your credentials/ Check the output"
      else
        echo "Successfully Created the lambda lambda_function"
      fi
    else
      echo "Please install terraform install your local machine"
    fi
  else
    echo "AWS ACCOUNT_ID is missing, please export the variable"
  fi
  echo "#############################"
  popd
else
  pushd ./terraform
  if [ "$action" = "destroy" ]; then
    echo "Generating jinja files and tfvars file"
    python ./Template.py
    echo "Completed Generating tfvars file and jinja file"
     terraform init 1> $SUCCESS_OUTPUT_PATH
     terraform state pull
     terraform destroy -var-file="./input_vars.tfvars" -auto-approve
  else
    echo "Invalid argument passed, supported only deploy, destroy"
  fi
  popd
fi
