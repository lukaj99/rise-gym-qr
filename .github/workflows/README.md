# GitHub Actions Setup for QR Code Scraping

## Required Secrets

You need to set up the following secrets in your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to Settings → Secrets and variables → Actions
3. Add the following repository secrets:

### RISE_GYM_USERNAME
Your Rise Gym login email/username

### RISE_GYM_PASSWORD  
Your Rise Gym login password

## Workflow Details

The `scrape-qr-codes.yml` workflow:
- Runs automatically every hour at 15 minutes past the hour
- Can be manually triggered from the Actions tab
- Scrapes QR codes from Rise Gym
- Commits any new QR codes back to the repository
- Updates the QR database JSON files

## Manual Trigger

To run the workflow manually:
1. Go to the Actions tab in your repository
2. Select "Scrape Rise Gym QR Codes" workflow
3. Click "Run workflow"
4. Select the branch and click "Run workflow"

## Monitoring

Check the Actions tab to monitor workflow runs and view logs if any issues occur.