# Automating Setting up n8n, FastAPI & Cloudflare Tunnel on Google Cloud

## Overview
This project contains a Python script designed to automate the setup of a free-tier Google Cloud Platform (GCP) [e2 micro-instance](https://cloud.google.com/free/docs/free-cloud-features#compute) with [n8n](https://n8n.io), [FastAPI](https://fastapi.tiangolo.com), and a [Cloudflare tunnel](https://www.cloudflare.com/products/tunnel/). The script uses Terraform to provision infrastructure on GCP. It automates several tasks, including generating a service account key, setting up a static IP, and configuring firewall rules.

### What the Python Script Does:
1. **Project ID Retrieval**: Fetches your GCP project ID using the Google Cloud CLI.
2. **Service Account Key Generation**: Creates and downloads a service account key for the default service account.
3. **Static IP Check/Create**: Checks for an existing static IP or creates a new one.
4. **Terraform Config Generation**: Creates a Terraform configuration file (`setup.tf`) to set up a GCP instance with necessary configurations.

### What the Terraform File Deploys:
The Terraform configuration (`setup.tf`) provisions the following on GCP:
- A new GCP instance with specified configurations e2 machine type, 60gb boot disk, and standard static IP network interfaces.
- A static IP address, ensuring the instance is accessible at a consistent IP.
- Optionally, a firewall rule to allow traffic on port 5678, needed for n8n.

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

### Modify Global Variables in Python Script:
- `n8n_hostname`: Set this to your domain (e.g., `n8n.yourdomain.com`).
- `webhook_url`: Set this to your webhook URL.
- `fastapi_docker_image`: Choose the FastAPI Docker image version.
- `region`: Default is `us-west1`; adjust if needed. Note: if you change this review the python script for the Zone to confirm you want to be in "-a"
- `ssh_key`: Add your SSH key.

### Deployment Steps:
1. Clone the GitHub repository.
2. Navigate to the local directory in the terminal.
3. Run the setup script with `python setup.sh`.
4. Initialize Terraform with `terraform init`.
5. Apply Terraform configuration with `terraform apply`. When prompted, type `yes`.

### Post-Deployment:
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
