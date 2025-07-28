# capstone_herovired

STEP 1: Create the .env File
Open your code folder.

Create a new file:
touch .env

Add this content (ask your team for actual values):
```bash
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AZURE_SUBSCRIPTION_ID=your_azure_id
#ReadOnly Access
MONGO_URI=mongodb+srv://Read-user:"ENTERPASSWORDHERE"@devops-cluster.6sb24j6.mongodb.net/devops_dashboard
```
Make sure .env is included in .gitignore to avoid pushing credentials to GitHub.
