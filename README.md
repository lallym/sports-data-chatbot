# sports-data-chatbot
This lab can be used to create a GenAI-powered chatbot that allows you to use natural language to query a database. We will make use of a number of AWS services including Cognito, S3, Lambda, Bedrock and Amplify Hosting.

# Step 1: Deploy Cognito Resources
We want our application to be secure, so we will use Amazon Cognito as our identity provider. Since Identity is an ancillary aspect of this lab, we will use a CloudFormation template to deploy the base Cognito resources.
1. In the AWS console in the us-east-1 region, navigate to CloudFormation.
2. Click the **Create Stack** button and select the "With new resources (standard)" option.
3. In the **Specify template** section click "Upload a template file".
4. Click the **Choose file** button and select and open the *cognito.yaml* file from this lab and click **Next**.
5. Specify an appropriate **Stack name** such as "cognito-stack".
6. For **AuthName** enter a prefix for this stack such as "chatbot" or "demo" then click **Next**.
7. Scroll to the bottom of the page, check the box to acknowledge the creation of IAM resources, and click **Next**.
8. Scroll to the bottom of the page and click **Create**.
9. After a few moments, the Cognito resources will be created. At that time, navigate to Cognito in the us-east-1 region.
10. We will need multiple pieces of information later, so we will note those down now. Click **User pools** from the menu on the left and then click on the name of the user pool that was just created.
11. Copy the "User pool ID" and paste it into your choice of notepad or text document for later use.
12. Scroll down and click on the tab labeled **App integration**. Then scroll down to the **App client list** section. Copy the **Client ID** of our app client for later use.
13. Click **Identity pools** in the left-side menu and copy the **Identity pool ID** of the newly created Identity pool for later use.

# Step 2: Create a Cognito User
1. In the AWS console in the us-east-1, navigate to Cognito.
2. Click **User pools** from the menu on the left.
3. Click the name of the user pool created by CloudFormation, for example *chatbot-user-pool* or *demo-user-pool*.
4. In the **Users** section of the page, click the **Create user** button.
5. Select "Send an email invitation" in the **Invitation message** section.
6. Enter your email address for **User name** and **Email address**.
7. For **Temporary password** select "Generate a password"
8. Click **Create user**.

# Step 3: Update Bedrock Model Access
1. In the AWS console in the us-east-1 region, navigate to Amazon Bedrock.
2. On the left-side menu, scroll to the **Bedrock configurations** section at the bottom and click on "Model access".
3. Click the **Modify model access** button.
4. Ensure the box next to "Claude 3 Sonnet" is checked and click **Next** at the bottom of the page.
5. Click **Submit**.

# Step 4: Modify the Web UI code
We've provided a rudimentary, JavaScript-powered UI to enable the chatbot. The code of the UI is largely outside the scope of this workshop, but there are some items we must update to ensure we can authenticate.
1. Navigate to the web-ui folder of this repo.
2. Open the *js/config.js* file in the editor of your choice.
3. On line 3, past the value of the User Pool ID we copied earlier inside the single quotes.
4. On line 4, paste the value of the Client ID we copied earlier inside the single quotes.
5. Save and close the *js/config.js* file.
6. Open the *js/cognito-auth.js* file in the editor of your choice.
7. On line 60, paste the value of the Identity Pool ID we copied earlier to replace the placeholder value inside the single quotes.
8. On line 63, replace *us-east-1_xxxxxx* with the value of our User Pool ID we copied earlier.
9. Save and close the *js/cognito-auth.js* file.
10. Open the *js/app.js* file in the editor of your choice.
11. On line 42, paste the value of the Identity Pool ID we copied earlier to replace the placeholder value inside the single quotes.
12. On line 45, replace *us-east-1_xxxxxx* with the value of our User Pool ID we copied earlier.
13. Save and close the *js/app.js* file.
14. Zip all of the contents of our web UI. If you are on a Unix/Linux OS, this can be accomplished with the command `zip -r web-ui.zip .` (don't forget the '.' at the end of that command to ensure the entire working directory is zipped).

# Step 5: Deploy the Web UI using Amplify
1. In the AWS console in the us-east-1 region, navigate to AWS Amplify.
2. Click on the **Create new app** button on the upper right-side of the screen.
3. Select the **Deploy without Git** radio button and click **Next**.
4. Click the **Choose .zip folder** button and find the *web-ui.zip* file we just created and click **Open**.
5. Click **Save and deploy** to deploy our app to Amplify Hosting.
6. When the deployment is complete, take note of the URL for the deployed Domain for later use.

# Step 6: Create an S3 Bucket for our CSV files
In a production environment, this type of chatbot would be backed by a relational database. For this demo, we will make use of CSV files that reside in S3.
1. In the AWS console in the us-east-1 region, navigate to Amazon S3.
2. Click the **Create bucket** button on the upper right-side of the screen.
3. Choose a globally unique name for your bucket, perhaps something of the form your_first_initial-your_last_name-chatbot-data (e.g. a-jassy-chatbot-data). If your last name is Wang, Mohamed, Garcia or Smith, you may need to be more creative.
4. Leave all other options as their defaults, scroll to the bottom of the page, and click the **Create bucket** button.
5. After the bucket is created, click on its name in the S3 console.
6. Click the **Upload** button on the upper right-side of the screen.
7. Click the **Add files** button and select the two files from the CSV folder in this repo and click **Open** on the dialogue box.
8. Click the **Upload** button back in the S3 Console to upload the files to S3. It may take a few seconds before you see the **Upload successful** banner displayed at the top of the screen.

# Step 7: Create a Lambda Layer and Function
The Lambda function is the primary interface between our UI and other AWS services to process the chat queries and responses.
1. In the AWS console in the us-east-1 region, navigate to Lambda.
2. Click "Layers" from the menu on the left and then click the **Create layer** button on the upper right-side of the screen.
3. For layer name input *duckdb-bs4*.
4. Click the **Upload** button and select the "duckdb_bs4_layer.zip" file from the lambda directory of this repo.
5. For **Compatible architectures** select "x86_64".
6. For **Compatible runtimes** select "Python 3.12".
7. Click the **Create** button at the bottom of the screen.
8. After the Layer is successfully created, click on "Lambda" in the cookie crumb menu in the upper left of the screen.
9. Click the **Create function** button on the upper right-side of the screen.
10. Ensure the "Author from scratch" radio button is selected.
11. For **Function name** enter *basketballChatbot*. It is important that our function is named precisely because we have other dependencies in our UI code.
12. For **Runtime** select *Python 3.12*.
13. Leave all other optionas as default and click the **Create function** button.
14. In the code editor window for the newly created function, replace the contents of the "lambda_function.py" file with the contents of "lambda_function.py" from the lambda directory of this repo.
15. On lines 243 and 246 of the code, replace "your-bucket-name" with the name of the S3 bucket we created above.
16. Type Ctrl+S (or Command+S if on a Mac) to save the code changes.
17. Scroll down to the **Layers** section and click on the **Add a layer** button.
18. Select **Custom layers**, choose the *duckdb-bs4* custom layer we created earlier, choose *1* for the Version and click **Add**
19. Above the **Code source** section click on the **Configuration** tab.
20. Click the **Edit** button in the **General configuration** section.
21. Change the **Timeout** to *2 min 30 sec*.
22. Ensure "Use an existing role" is selected in the **Execution role** section and make note of the role name in the **Existing role** dropdown box. If no role is show, click the circle refresh icon to the right of the dropdown box.
23. Click the **Save** button.
24. Click the **Code** tab and then clikc the **Deploy** button to deploy our function.

# Step 8: Update the Lambda Execution Role
1. In the AWS console, navigate to IAM.
2. Click on **Roles** in the menu on the left of the screen.
3. In the *Roles* that are returned, find the execution role for our Lambda and click on its name. If you cannot easily find the role, you can enter "chatbot" in the *Search* bar to find it.
4. In the **Permissions** section click on the **Add permissions** button and select *Attach policies*.
5. In the *Search* box enter "bedrock" and select the **AmazonBedrockFullAccess** policy.
6. In the *Search* box replace "bedrock" with "s3" and select the **AmazonS3FullAccess** policy.
7. Scroll to the botttom of the screen and click the **Add permissions** button.

# Step 9: Test Your Chatbot
1. Navigate to the Amplify Domain URL that we copied earlier when we deployed our web UI.
2. Check your email for a message from *no-reply* with the subject "You've been invited to test the Basketball Chatbot".
3. Note the username and password from that email and enter them into the UI and click the **SIGN IN** button.
4. You will be prompted to change your password, so enter a new password and click the **CHANGE PASSWORD** button.
5. Once logged in, begin testing the application using the recommended prompts.

# Step 10: Congratulations!
You did it! You've deployed a GenAI-powered chatbot that takes a natural language question related to a data set, devises an appropriate SQL query, and returns a contextual response!
