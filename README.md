# Automated Configuration of n8n, FastAPI & Cloudflare Tunnel on E2 Free Tier Google Cloud

## Overview
This project contains a Python script designed to automate the setup of a free-tier Google Cloud Platform (GCP) [e2 micro-instance](https://cloud.google.com/free/docs/free-cloud-features#compute) with [n8n](https://n8n.io), [FastAPI](https://fastapi.tiangolo.com), and a [Cloudflare tunnel](https://www.cloudflare.com/products/tunnel/). The script uses Terraform to provision infrastructure on GCP. It automates several tasks, including generating a service account key, setting up a static IP, and configuring firewall rules.

### What the Python Script Does:
1. **Project ID Retrieval**: Fetches your GCP project ID using the Google Cloud CLI.
2. **Service Account Key Generation**: Creates and downloads a service account key for the default service account.
3. **Static IP Check/Create**: Checks for an existing static IP or creates a new one.
4. **Terraform Config Generation**: Creates a Terraform configuration file (`setup.tf`) to set up a GCP instance with necessary configurations.
5. **Generates Scripts and Configuration Files**: setup_server.sh, setup_cloudflare.sh, docker-compose.yml, and docker-compose.service

### What the Terraform File Deploys:
The Terraform configuration (`setup.tf`) provisions the following on GCP:
- A new GCP instance with specified configurations e2 machine type, 60gb boot disk, and standard static IP network interfaces.
- Uploads files to the server: /opt/setup_server.sh, /opt/setup_cloudflare.sh, /opt/docker-compose.yml, and /etc/systemd/system/docker-compose.service
- A firewall rule to allow traffic on port 5678, needed for n8n (but since most will use Cloudflare Tunnel probably unneccessary.)

### Server Setup Scripts:
Two scripts must be run on the server
1. `setup_server.sh`: Installs Docker, Apache2, wget, n8n, and FastAPI on the GCP instance.
2. `setup_cloudflare.sh`: Sets up a Cloudflare tunnel for SSL, downloads `cloudflared`, and configures it to route traffic to the n8n service.

## Prerequisites
- Terraform: [Installation Guide](https://developer.hashicorp.com/terraform/install)
- Google Cloud SDK: [Installation Guide](https://cloud.google.com/sdk/docs/install)
- Python 3: Confirm its installed on your machine: `python3 --version`
- SSH Key: [Generate an SSH key for GitHub](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
- Domain with Cloudflare DNS: [Sign up and host a domain](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/) to be able to configure [Cloudflare tunnel](https://www.cloudflare.com/products/tunnel/).

## Usage
It will take around 20 minutes to configure the server. Most of the time takes place in step 3 where the scripts are downloading files.

### Step 1: Modify Global Variables in the Python Script:
- `n8n_hostname`: Required. Set this to your domain (e.g., `n8n.yourdomain.com`).
- `webhook_url`: Optional. Set this to your webhook URL. (will default to your n8n_hostname)
- `fastapi_docker_image`: Optional. Choose the FastAPI Docker image version if you prefer a diff version.
- `region`: Optional. Default is `us-west1`; adjust if needed. Note: if you change this review the python script for the Zone to confirm you want to be in "-a"
- `ssh_key`: Required. Add your SSH key.
- `ssh_private_key_path`: Required. Path to local private key "/Users/username/.ssh/gcp"
- `ssh_user` = Required. ssh key username.

### Step 2: Deployment Steps:
1. Clone the GitHub repository.
2. Navigate to the local directory in the terminal.
3. Run the setup script with `python setup.sh`.
4. Initialize Terraform with `terraform init`.
5. Apply Terraform configuration with `terraform apply`. When prompted, type `yes`.

### Step 3: Post-Deployment:
- SSH into your server: `ssh -i ~/.ssh/gcp USERNAME@X.X.X.X`
- Run setup scripts on the server:
  - `sudo sh /opt/setup_server.sh`
  - `sudo sh /opt/setup_cloudflare.sh`
  - Follow the instructions to set up the Cloudflare tunnel. When prompted, copy/paste the URL in a browser and then select the domain you want to tunnel and authorize it. The cert will be downloaded to the server and your DNS name will be updated with the tunnelID.

## Cost Considerations
- The E2 micro instance is under GCP's always-free tier, implying no cost for 24/7 operation. However, always verify with Google's latest policies. Cloudflare Tunnel, FastAPI, n8N are also free to use but verify with their latest policies.

## SSL Setup
- This script configures SSL using a Cloudflare tunnel.

## Debugging and FAQs
- **If You Experience Service Account Key Issues You Can List/Delete**:
  - List Keys: `gcloud iam service-accounts keys list --iam-account <account-id>`
  - Delete Keys: `gcloud iam service-accounts keys delete <key-id> --iam-account <account-id>`
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
  - Check Logs for Further Errors: If the issue persists, check the logs again for any additional errors. Use sudo journalctl -u docker-compose.service to review the service logs and sudo docker logs [container_id] for container logs.
  - Review Restart Policy: The container's exit code 0 suggests it exited cleanly. Review the restart policy in the Docker Compose file to ensure it aligns with your desired behavior. A policy like restart: unless-stopped might be appropriate.
  - Docker Compose File: If you need to review the docker-compose.yml file it's located at `/opt/docker-compose.yml`.
  - Verify the service is running correctly
  ```
  sudo systemctl status docker-compose.service
  sudo docker ps
  ```

 ## Video Walkthrough
 [![18 minute video demonstrating setup](http://img.youtube.com/vi/91-i_IIa8PQ/0.jpg)](http://www.youtube.com/watch?v=91-i_IIa8PQ "Video Title")

## How to Delete What This Script Creates
On Google Cloud
1. [Firewall Policy](https://console.cloud.google.com/net-security/firewall-manager/firewall-policies) : A Firewall policy is created on port 5678. This can be deleted via the Firewall Policies section in GCP.
2. [VM](https://console.cloud.google.com/compute/instances): A Virtual Machine (VM) is created. This can be deleted via the VM Instances section in GCP.
3. [Standard Static IP](https://console.cloud.google.com/networking/addresses): A standard static IP is created. This should be released via the External IP addresses section in GCP.

On [Cloudflare](https://cloudflare.com)
1. Tunnel: A tunnel is created which can be deleted by navigating to Zero Trust > Access > Tunnels in the Cloudflare Dashboard (login required).
2. Subdomain with Tunnel: A subdomain is created on your chosen domain with a tunnel. This can be deleted by going to your domain's DNS settings at Choose your domain > DNS in the Cloudflare Dashboard (login required) and looking for the CNAME on your Domain.

## Known Issues
These might both be related to docker-compose implementations will investigate
1. On reboot Docker and containers (n8n and FastAPI) are not auto-starting correctly
2. On reboot n8n seems to wipe the data (it's got access to 60gb of persistent data need to figure out what's up) 
