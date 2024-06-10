#!/bin/bash

PROJECT_NAME="AggFunction"
SUCCESS_OUTPUT_PATH="/dev/null"
ERROR_LOG="$(mktemp -d)/stderr.log"


echo "Clearing if previously created zip file"
PROJECT_PATH="$PWD/$PROJECT_NAME.zip"
if [ -f $PROJECT_PATH ]; then
    rm -rf  $PROJECT_PATH
    rm -rf ./package
    echo "Deleted Previously created zip file"
fi

pip install --upgrade pip
pip install --target ./package -r ../requirements.txt > $SUCCESS_OUTPUT_PATH
pushd package
zip -r ../$PROJECT_NAME.zip . > $SUCCESS_OUTPUT_PATH
popd
zip -g $PROJECT_NAME.zip lambda_function.py > $SUCCESS_OUTPUT_PATH
zip -g $PROJECT_NAME.zip ../es_operations.py > $SUCCESS_OUTPUT_PATH
zip -g $PROJECT_NAME.zip ../send_email.py > $SUCCESS_OUTPUT_PATH
aws lambda update-function-code --function-name CloudSenseiAggFunction --zip-file fileb://$PROJECT_PATH --region $AWS_DEFAULT_REGION > $SUCCESS_OUTPUT_PATH
