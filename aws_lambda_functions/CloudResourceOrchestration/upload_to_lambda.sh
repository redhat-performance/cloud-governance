PROJECT_NAME="CloudResourceOrchestration"
SUCCESS_OUTPUT_PATH="/dev/null"
AWS_DEFAULT_REGION="us-east-1"
echo "Clearing if previously created zip file"

PROJECT_PATH="$PWD/$PROJECT_NAME.zip"

if [ -f $PROJECT_PATH ]; then
    rm -rf  $PROJECT_PATH
    rm -rf ./package
    echo "Deleted Previously created zip file"
fi

pip install --target ./package -r requirements.txt > $SUCCESS_OUTPUT_PATH
pushd package
zip -r ../$PROJECT_NAME.zip . > $SUCCESS_OUTPUT_PATH
popd
zip -g $PROJECT_NAME.zip lambda_function.py > $SUCCESS_OUTPUT_PATH

echo "#############################"
# Uploading to AWS Lambda
echo "Uploading to AWS Lambda install Region: $AWS_DEFAULT_REGION"
aws lambda update-function-code --function-name CloudResourceOrch --zip-file fileb://$PROJECT_PATH --region $AWS_DEFAULT_REGION > $SUCCESS_OUTPUT_PATH
echo "Uploaded to AWS Lambda"
echo "#############################"
