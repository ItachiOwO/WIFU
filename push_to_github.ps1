# Git commands to push the WiFU project to GitHub
# Save this file and run it from PowerShell

$projectPath = "C:\Users\aryan\OneDrive\Desktop\src files\WiFU"
$repoUrl = "https://github.com/ItachiOwO/WIFU.git"

# Navigate to your project directory
Set-Location $projectPath

# Initialize git repository (if not already done)
if (-not (Test-Path ".git")) {
    Write-Host "Initializing git repository..."
    git init
}

# Add the remote repository
Write-Host "Adding remote repository..."
git remote remove origin 2>$null # Remove if exists
git remote add origin $repoUrl

# Add all files to git
Write-Host "Adding files to git..."
git add .

# Commit changes
Write-Host "Committing changes..."
git commit -m "Complete transformation from pwnagotchi to WiFU"

# Push to GitHub
Write-Host "Pushing to GitHub..."
Write-Host "You may be prompted for your GitHub credentials or personal access token"
git push -u origin main

Write-Host "Done! Check for any errors above."
