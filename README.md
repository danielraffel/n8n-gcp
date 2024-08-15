# Automated Configuration of n8n, FastAPI & Cloudflare Tunnel on E2 Free Tier Google Cloud

**TL;DR** Automate n8n, FastAPI, and Cloudflare Tunnel setup on Google Cloud with a comprehensive Python script that uses Terraform to deploy your customized configuration.

**To jump to the installation instructions,** see the [Prerequisites](#prerequisites) and [Usage](#usage) sections.

## Overview
This project contains a Python script designed to automate the setup of a free-tier Google Cloud Platform (GCP) [e2 micro-instance](https://cloud.google.com/free/docs/free-cloud-features#compute) with [n8n](https://n8n.io), [FastAPI](https://fastapi.tiangolo.com), and a [Cloudflare tunnel](https://www.cloudflare.com/products/tunnel/). The script uses Terraform to provision infrastructure on GCP. It automates several tasks, including generating a service account key, setting up a static IP, and installing scripts on the server to assist with installing and updating software.

### What the Python Script Does:
1. **Project ID Retrieval**: Fetches your GCP project ID using the Google Cloud CLI.
2. **Service Account Key Generation**: Creates and downloads a service account key for the default service account.
3. **Static IP Check/Create**: Checks for an existing static IP or creates a new one.
4. **Terraform Config Generation**: Creates a Terraform configuration file (`setup.tf`) to set up a GCP instance with necessary configurations.
5. **Generates Scripts and Configuration Files**: `setup_server.sh`, `setup_cloudflare.sh`, `updater.sh`, `docker-compose.yml`, `Dockerfile`, `docker-entrypoint.sh`, and `docker-compose.service`.
6. **No-Upload Mode**: Allows you to generate all necessary configuration files and scripts without uploading them to the cloud. This feature is useful if you want to preview or modify the generated files before deploying to Google Cloud. You can activate this mode by running the script with the `--no-upload` flag eg `python setup.sh --no-upload`. If you later decide to proceed with the full setup, you will need to run the script from scratch without the `--no-upload` flag to generate and upload the files to Google Cloud eg `python setup.sh`.

### What the Terraform File Deploys:
The Terraform configuration (`setup.tf`) provisions the following on GCP:
- A new (free) GCP instance consisting of an e2 micro-instance with a 60GB boot disk, and standard static IP network interface.
- Uploads files to the server: `/opt/setup_server.sh`, `/opt/setup_cloudflare.sh`, `/opt/updater.sh`, `/opt/docker-compose.yml`, `/etc/systemd/system/docker-compose.service`, `/opt/Dockerfile`, and `/opt/docker-entrypoint.sh`.

### Explanation of Generated Files
1. **Dockerfile**:
   - The `Dockerfile` is used to create a custom Docker image for n8n. This custom image is based on the official n8n image but includes additional npm packages, specifically `n8n-nodes-socket.io`, which enables WebSocket commands. If you prefer not to install this package or want to use a different community node, you can comment out or replace the relevant lines in the Dockerfile. For example, you can use the [GUI installation method](https://docs.n8n.io/integrations/community-nodes/installation/gui-install/) to install different community nodes.
2. **docker-entrypoint.sh**:
   - The `docker-entrypoint.sh` file serves as the entry point for the custom n8n Docker container. It ensures that the necessary directories are created and owned by the appropriate user (`node`) before starting the n8n service. This script is executed whenever the container is started.
3. **docker-compose.yml**:
   - The `docker-compose.yml` file defines the services and configurations required to run n8n and FastAPI within Docker containers. It specifies the custom n8n image, port mappings, environment variables, and volumes. Specifically, the following environment variable is included for WebSocket support:

     ```yaml
     environment:
       - NODE_FUNCTION_ALLOW_EXTERNAL=socket.io,socket.io-client
     ```

     This variable (`NODE_FUNCTION_ALLOW_EXTERNAL`) allows the n8n instance to use external packages like `socket.io` and `socket.io-client`, which are installed via the Dockerfile. If you disable or replace the `n8n-nodes-socket.io` package, you can comment out or modify this environment variable accordingly.

     Example of commenting out:
     ```yaml
     # environment:
     #   - NODE_FUNCTION_ALLOW_EXTERNAL=socket.io,socket.io-client
     ```

     Or replace it with another node package that you have installed:
     ```yaml
     environment:
       - NODE_FUNCTION_ALLOW_EXTERNAL=another-package
     ```
4. **setup_server.sh**:
   - The `setup_server.sh` script is executed on the server to install Docker, build the custom n8n image, and start the Docker containers using Docker Compose. It ensures that Docker is correctly installed and configured on your GCP instance and builds the custom n8n image using the Dockerfile. This script is essential for initializing the server with all the necessary components.
5. **setup_cloudflare.sh**:
   - The `setup_cloudflare.sh` script sets up a Cloudflare tunnel to provide SSL encryption for your n8n instance. It downloads and installs the Cloudflare daemon (`cloudflared`), configures a tunnel, and associates it with your chosen subdomain. This script ensures that your n8n instance is securely accessible over HTTPS.
6. **updater.sh**:
   - The `updater.sh` script is designed to update your server's software components, including Docker, n8n, FastAPI, and Cloudflare Tunnel. It pulls the latest base image for n8n, rebuilds the custom n8n image, and restarts the Docker containers. This script ensures that your setup remains up-to-date with the latest versions of the software.

### Server Setup Scripts:
Two scripts must be run on the server:
1. `setup_server.sh`: Installs [Docker using their repository](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository), builds the custom n8n image, and installs FastAPI on a GCP Ubuntu 22.04 micro-server instance.
2. `setup_cloudflare.sh`: Sets up a Cloudflare tunnel for SSL, downloads `cloudflared`, and configures it at a subdomain to route traffic to the n8n service.

## [Prerequisites](#prerequisites)
- Terraform: [Installation Guide](https://developer.hashicorp.com/terraform/install)
- Google Cloud SDK: [Installation Guide](https://cloud.google.com/sdk/docs/install)
- Python 3: Confirm it's installed on your machine: `python3 --version`
- SSH Key: [Generate an SSH key (how to guide by GitHub)](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
- Domain with Cloudflare DNS: [Sign up and host a domain](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/) to be able to configure [Cloudflare tunnel](https://www.cloudflare.com/products/tunnel/).

## [Usage](#usage)
It will take around 20 minutes to configure the server. Most of the time takes place in step 3 where the scripts are downloading files.

### Step 1: Personalize Global Variables in the Python Script:
- `n8n_hostname`: Required. Set this to your domain (e.g., `n8n.yourdomain.com`).
- `webhook_url`: Optional. Set this to your webhook URL. (will default to your n8n_hostname)
- `fastapi_docker_image`: Optional. Choose the FastAPI Docker image version if you prefer a different version.
- `region`: Optional. Default is `us-west1`; adjust if needed. Note: if you change this, review the Python script for the Zone to confirm you want to be in `-a`.
- `ssh_key`: Required. Add your SSH key.
- `ssh_private_key_path`: Required. Path to local private key `/Users/username/.ssh/gcp`.
- `ssh_user`: Required. SSH key username.

### Step 2: Deployment Steps:
1. Clone the GitHub repository
   ```bash
   https://github.com/danielraffel/n8n-gcp.git
   ```
2. Navigate to the local directory in the terminal
   ```bash
   cd n8n-gcp
   ```
3. Run the setup script in a terminal
   ```bash
   python setup.sh
   ```
4. Initialize Terraform
   ```bash
   terraform init
   ```
5. Apply Terraform configuration
   ```bash
   terraform apply
   ```
   When prompted to deploy, type `yes`.

### Step 3: Post-Deployment:
6. SSH into your server in a terminal:
   ```bash
   ssh -i ~/.ssh/gcp USERNAME@X.X.X.X
   ```
7. Install setup scripts on the server (to install and configure Docker, n8n, FastAPI):
   ```bash
   sudo sh /opt/setup_server.sh
   ```
   Follow the instructions when prompted to install software that will require additional disk space, type `y` (this is the Docker software from their repository).

8. Install Cloudflare setup scripts on the server to get SSL:
   ```bash
   sudo sh /opt/setup_cloudflare.sh
   ```
   Follow the instructions to set up the Cloudflare tunnel. When prompted, copy/paste the URL in a browser and then select the domain you want to tunnel and authorize it. The cert will be downloaded to the server and your DNS name will be updated with the tunnelID.

## Cost Considerations
- The [E2 micro-instance](https://cloud.google.com/free/docs/free-cloud-features#compute) is under GCP's always-free tier, implying no cost for 24/7 operation within their defined limits. However, always verify the latest policies with Google, Cloudflare Tunnel, FastAPI, and n8n to ensure you understand their latest policies.

## SSL Setup
- This script configures SSL using a Cloudflare tunnel and will add a subdomain to your DNS nameserver.

## Updating Server Software
1. SSH into your server in a terminal:
   ```bash
   ssh -i ~/.ssh/gcp USERNAME@X.X.X.X
   ```
2. Run the updater script on the server (to upgrade Docker, n8n, FastAPI, and Cloudflare Tunnel):
   ```bash
   sudo sh /opt/updater.sh
   ```
## Testing the `n8n-nodes-socket.io` Installation
To verify that the `n8n-nodes-socket.io` package is installed and working correctly, you can copy/paste the following code in an n8n workflow:

```json
{
  "meta": {
    "instanceId": "84c8cadeffb0e45ffb93507bd03ee1ba65b1274dc2bab04cc058f9e6a2a130e1"
  },
  "nodes": [
    {
      "parameters": {
        "jsCode": "const io = require('socket.io-client');\n\n// Setup promise to handle WebSocket response\nreturn new Promise((resolve, reject) => {\n  const serverUrl = 'wss://ws.postman-echo.com/socketio';\n  const socket = io(serverUrl, { transports: ['websocket'] });\n\n  // Connect event\n  socket.on('connect', () => {\n    console.log('Connected to WebSocket server');\n    // Send a message upon connection\n    socket.emit('message', 'Hello, Postman!');\n  });\n\n  // Message event\n  socket.on('message', (data) => {\n    console.log('Message received:', data);\n    // Resolve the promise after receiving a message\n    // Ensure we close the socket connection\n    socket.disconnect();\n    resolve([{ json: { message: data } }]); // Return received data\n  });\n\n  // Disconnect event\n  socket.on('disconnect', () => {\n    console.log('Disconnected from WebSocket server');\n  });\n\n  // Error event\n  socket.on('error', (error) => {\n    console.log('WebSocket error:', error);\n    reject([{ json: { error: error.message } }]); // Handle errors\n  });\n});\n"
      },
      "id": "4fec8380-98a1-4282-b172-de6528b34893",
      "name": "Code6",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [
        340,
        580
      ]
    }
  ],
  "connections": {},
  "pinData": {}
}
```

## Debugging and FAQs
- **If You Experience Service Account Key Issues You Can List/Delete**:
  - List Keys: `gcloud iam service-accounts keys list --iam-account <YOURACCOUNTSTRING-compute@developer.gserviceaccount.com>`
  - Delete Keys: `gcloud iam service-accounts keys delete <key-id> --iam-account <YOURACCOUNTSTRING-compute@developer.gserviceaccount.com>`
  - Note: you can find your IAM account in the file that's generated on your machine called `service-account-key.json`
- **Example SSH Key String**: `service_account:ssh-rsa SDqhy5jXUv3xKGhzYJzjALiHg6ZzWKSSrhbjXVAvp6SecWdZPkGw16UhHHTCHvD4bwjnH6NXjHtyuCVqhdDuY1+E1BSdf0G0rncN8qFrzT1imJqraru38UEJRTZFrXMG6Kvx698J[ELvapEXXMv52zW6ZwHuU5aJ0t2atDHEXha7V3UAKSbgxLbbtQGRgtANcz3fvk9ve8GVPEtB3Cyz3eyg4aBHVqLyxx3N9hithMe`
- **View Server Setup Output**: Check `/var/log/startup_script.log`.
- **Managing Cloudflared Tunnels When SSHd On Server**:
  - List: `cloudflared tunnel list`
  - Delete: `cloudflared tunnel delete <tunnel_name>`
- **Managing Cloudflared Service**:
  - Start/Stop: `sudo systemctl start/stop cloudflared`
  - Check Status: `sudo systemctl status cloudflared`
- **Monitoring Docker**:
  - After restarting, monitor the service and container status to ensure they are running as expected. Use `sudo systemctl status docker-compose.service` for the service and `sudo docker ps` to check the running containers.
  - Check Logs for Further Errors: If the issue persists, check the logs again for any additional errors. Use `sudo journalctl -u docker-compose.service` to review the service logs and `sudo docker logs [container_id]` for container logs.
  - Review Restart Policy: The container's exit code 0 suggests it exited cleanly. Review the restart policy in the Docker Compose file to ensure it aligns with your desired behavior. A policy like `restart: unless-stopped` might be appropriate.
  - Docker Compose File: If you need to review the `docker-compose.yml` file it's located at `/opt/docker-compose.yml`.
  - Verify the service is running correctly
   ```bash
   sudo systemctl status docker-compose.service
   sudo docker ps
   ```

## Video Walkthrough [outdated]
[![18 minute video demonstrating setup](http://img.youtube.com/vi/91-i_IIa8PQ/0.jpg)](http://www.youtube.com/watch?v=91-i_IIa8PQ "Video Title")

## How to Delete What This Script Creates
On Google Cloud:
1. [VM](https://console.cloud.google.com/compute/instances): A Virtual Machine (VM) is created. This can be deleted via the VM Instances section in GCP.
2. [Standard Static IP](https://console.cloud.google.com/networking/addresses): A standard static IP is created. This should be released via the External IP addresses section in GCP (if a standard reserved IP is not attached to anything you will be charged so be certain to release it).

On [Cloudflare](https://cloudflare.com):
1. Tunnel: A tunnel is created which can be deleted by navigating to Zero Trust > Access > Tunnels in the Cloudflare Dashboard (login required).
2. Subdomain with Tunnel: A subdomain is created on your chosen domain with a tunnel. This can be deleted by going to your domain's DNS settings at Choose your domain > DNS in the Cloudflare Dashboard (login required) and looking for the CNAME on your Domain.

## ToDo
- Configure uvicorn-gunicorn-fastapi post installation.
- Update script to run on Windows and confirm it runs on Linux. Currently, optimized for macOS. Changes should be minimal and limited to platform-specific commands.
- Explore running the server side scripts using Terraform.
- Update the video walkthrough which is now outdated.
