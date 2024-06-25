#!/bin/bash

# Function to display the menu
show_menu() {
    echo "Choose a deployment option for Vercel:"
    echo "1) Deploy using Vercel CLI"
    echo "2) Deploy using Git integration"
    echo "3) Deploy using Vercel Dashboard"
    echo "4) Install and configure Vercel CLI"
    echo "5) Exit"
}

# Function to deploy using Vercel CLI
deploy_with_cli() {
    echo "Deploying using Vercel CLI..."
    # Ensure Vercel CLI is installed
    if ! command -v vercel &> /dev/null
    then
        echo "Vercel CLI not found, installing..."
        npm install -g vercel
    fi

    # Initialize Vercel project
    vercel init

    # Deploy the project
    vercel --prod
}

# Function to deploy using Git integration
deploy_with_git() {
    echo "Deploying using Git integration..."
    echo "Please ensure your project is pushed to a Git repository (GitHub, GitLab, or Bitbucket)."
    echo "Visit the Vercel dashboard to import your project and set up automatic deployments."
    echo "Opening Vercel dashboard..."
    xdg-open "https://vercel.com/dashboard" || open "https://vercel.com/dashboard"
}

# Function to deploy using Vercel Dashboard
deploy_with_dashboard() {
    echo "Deploying using Vercel Dashboard..."
    echo "Visit the Vercel dashboard to create a new project and deploy your application."
    echo "Opening Vercel dashboard..."
    xdg-open "https://vercel.com/dashboard" || open "https://vercel.com/dashboard"
}

# Function to install and configure Vercel CLI
install_and_configure_vercel_cli() {
    echo "Installing Vercel CLI..."
    npm install -g vercel

    echo "Vercel CLI installed successfully."

    echo "Please log in to Vercel."
    vercel login

    echo "Generating Vercel API token..."
    echo "Please visit the following URL to create an API token: https://vercel.com/account/tokens"
    echo "Enter your Vercel API token:"
    read -s vercel_api_token

    echo "Configuring Vercel CLI with API token..."
    export VERCEL_API_TOKEN=$vercel_api_token
    echo "export VERCEL_API_TOKEN=$vercel_api_token" >> ~/.bashrc
    source ~/.bashrc

    echo "Vercel CLI configured successfully."
}

# Main script logic
while true; do
    show_menu
    read -p "Enter your choice [1-5]: " choice
    case $choice in
        1)
            deploy_with_cli
            ;;
        2)
            deploy_with_git
            ;;
        3)
            deploy_with_dashboard
            ;;
        4)
            install_and_configure_vercel_cli
            ;;
        5)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid choice, please try again."
            ;;
    esac
done