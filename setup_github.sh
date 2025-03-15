#!/bin/bash
# Script to set up and push the Proxmox-AI repository to GitHub

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Proxmox-AI GitHub Setup ===${NC}"
echo "This script will help you set up and push your Proxmox-AI codebase to GitHub"

# 1. Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}Git is not installed. Please install git first.${NC}"
    exit 1
fi

# 2. Navigate to the repository
cd "$(dirname "$0")"
REPO_DIR=$(pwd)
echo -e "${GREEN}Working directory:${NC} $REPO_DIR"

# 3. Check if this is already a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}Not a git repository. Please initialize git first with 'git init'.${NC}"
    exit 1
fi

# 4. Ask for GitHub username and repository name
read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter the repository name (default: proxmox-ai): " REPO_NAME
REPO_NAME=${REPO_NAME:-proxmox-ai}

# 5. Check if the remote already exists
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REMOTE_URL" ]; then
    echo -e "${YELLOW}Setting up new remote origin...${NC}"
    git remote add origin "git@github.com:$GITHUB_USERNAME/$REPO_NAME.git"
else
    echo -e "${YELLOW}Remote origin already exists. Updating it...${NC}"
    git remote set-url origin "git@github.com:$GITHUB_USERNAME/$REPO_NAME.git"
fi

# 6. Handle submodules
echo -e "${YELLOW}Checking submodules...${NC}"
if [ -f ".gitmodules" ]; then
    echo -e "${YELLOW}Submodules found. Initializing...${NC}"
    git submodule update --init --recursive || echo -e "${RED}Failed to update submodules, but continuing...${NC}"
fi

# 7. Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}You have uncommitted changes.${NC}"
    read -p "Do you want to commit all changes? (y/n): " COMMIT_CHANGES
    if [[ $COMMIT_CHANGES =~ ^[Yy]$ ]]; then
        git add .
        read -p "Enter commit message (default: Update Proxmox-AI codebase): " COMMIT_MSG
        COMMIT_MSG=${COMMIT_MSG:-"Update Proxmox-AI codebase"}
        git commit -m "$COMMIT_MSG"
    else
        echo -e "${RED}Please commit your changes before pushing.${NC}"
        exit 1
    fi
fi

# 8. Ensure we're on a branch (main or master)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "HEAD" ]; then
    echo -e "${YELLOW}Not on a branch. Creating 'main' branch...${NC}"
    git checkout -b main
    CURRENT_BRANCH="main"
fi

# 9. Push to GitHub with SSH URL
echo -e "${GREEN}Pushing to GitHub using SSH...${NC}"
echo -e "${YELLOW}Make sure you have SSH keys set up with GitHub${NC}"
echo -e "If you don't have SSH keys set up, please follow these instructions:"
echo -e "https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent"
echo -e "and then add the key to your GitHub account."
echo -e ""
read -p "Ready to push? (y/n): " READY_TO_PUSH

if [[ $READY_TO_PUSH =~ ^[Yy]$ ]]; then
    git push -u origin $CURRENT_BRANCH
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Successfully pushed to GitHub!${NC}"
        echo -e "Your repository is now available at: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
    else
        echo -e "${RED}Failed to push to GitHub.${NC}"
        echo -e "Try pushing manually with: git push -u origin $CURRENT_BRANCH"
    fi
else
    echo -e "${YELLOW}Push cancelled. You can push manually later with:${NC}"
    echo -e "git push -u origin $CURRENT_BRANCH"
fi

echo -e "${GREEN}Setup complete!${NC}"
