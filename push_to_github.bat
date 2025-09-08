@echo off
REM Git commands to push the WiFU project to GitHub

set projectPath=C:\Users\aryan\OneDrive\Desktop\src files\WiFU
set repoUrl=https://github.com/ItachiOwO/WIFU.git

REM Navigate to your project directory
cd /d "%projectPath%"

REM Initialize git repository (if not already done)
if not exist ".git" (
    echo Initializing git repository...
    git init
)

REM Add the remote repository
echo Adding remote repository...
git remote remove origin 2>nul
git remote add origin %repoUrl%

REM Add all files to git
echo Adding files to git...
git add .

REM Commit changes
echo Committing changes...
git commit -m "Complete transformation from pwnagotchi to WiFU"

REM Push to GitHub
echo Pushing to GitHub...
echo You may be prompted for your GitHub credentials or personal access token
git push -u origin main

echo Done! Check for any errors above.
pause
