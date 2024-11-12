# sports-data-chatbot
This lab can be used to create a GenAI-powered chatbot that allows you to use natural languahe to query a database. We will make use of a number of AWS services including Cognito, S3, Lambda, Bedrock and Amplify Hosting.

# Step 1: Deploy Cognito Resources
We want our application to be secure, so we will use Amazon Cognito as our identity provider. Since Identity is an anciallry aspect of this lab, we will use a CloudFormation template to deploye the base Cognito resources.
1. In the AWS console in the us-east-1 region, navigate to CloudFormation.
2. Run cognito.yaml

# Step 2: Update Bedrock Model Access
1. In the AWS console in the us-east-1 region, navigate to Bedrock.
2. 

# Step 3: Modify the Web UI code
1. Download web_ui.zip and update cognito information.

# Step 4: Deploy the Web UI using Amplify
1. Rezip and create Amplify deployment.

# Step 5: Create an S3 Bucket for our CSV files
1. Create S3 bucket and upload files to S3

# Step 6: Create a Lambda Function
The method through which our Web UI will connect to Create lambda with name specified in web_ui. Add lambda layer.

# Step 7: Update the Lambda Execution Role
1. update lambda execution role to access Bedrock and S3

# Step 8: Test Your Chatbot
1. Navigate to the 

