import subprocess
import json
import os
import argparse
import sys

# Global variables
n8n_hostname = "n8n.YOURDOMAIN.COM" # Required. Example: n8n.generouscorp.com
webhook_url = f"https://{n8n_hostname}/" # Note: this subdomain is added to your DNS when you configure Cloudflare Tunnnel via setup_cloudflare.sh
fastapi_docker_image = "tiangolo/uvicorn-gunicorn-fastapi:python3.11"
region = "us-west1"
ssh_key = "user_name:ssh-rsa string" # Required. Example: service_account:ssh-rsa SDqhy5jXUv3xKGhzYJzjALiHg6ZzWKSSrhbjXVAvp6SecWdZPkGw16UhHHTCHvD4bwjnH6NXjHtyuCVqhdDuY1+E1BSdf0G0rncN8qFrzT1imJqraru38UEJRTZFrXMG6Kvx698J[ELvapEXXMv52zW6ZwHuU5aJ0t2atDHEXha7V3UAKSbgxLbbtQGRgtANcz3fvk9ve8GVPEtB3Cyz3eyg4aBHVqLyxx3N9hithMe
ssh_private_key_path = "/Users/danielraffel/.ssh/gcp" # Required. Update to your private key path
ssh_user = "daniel_raffel" # Required. Update to your SSH key user_name

def main():
    # Change the working directory to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

def fetch_project_id():
    # Fetch project ID using Google Cloud CLI
    result = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
    return result.stdout.strip()

def fetch_service_account_key():
    # Fetch service account details
    accounts = subprocess.run(["gcloud", "iam", "service-accounts", "list", "--format=json"], capture_output=True, text=True)
    accounts_json = json.loads(accounts.stdout)

    # Look for the Compute Engine default service account
    compute_engine_service_account = None
    for account in accounts_json:
        if 'Compute Engine default service account' in account.get('displayName', ''):
            compute_engine_service_account = account["email"]
            break

    if not compute_engine_service_account:
        print("Compute Engine default service account not found.")
        return None

    # Creating a service account key
    key_filename = f"service-account-key.json"
    create_key_result = subprocess.run(
        ["gcloud", "iam", "service-accounts", "keys", "create", key_filename, "--iam-account", compute_engine_service_account],
        capture_output=True, text=True
    )

    if create_key_result.returncode != 0:
        # Handle error in key creation
        print("Error creating service account key:", create_key_result.stderr)
        return None

    return key_filename

def format_hostname(hostname):
    # Format hostname to comply with GCP naming conventions
    return hostname.replace('.', '-')

def check_static_ip(hostname, region):
    formatted_hostname = format_hostname(hostname)
    # Check if the static IP exists
    result = subprocess.run(["gcloud", "compute", "addresses", "list", "--filter=NAME=" + formatted_hostname + " AND region:" + region, "--format=json"], capture_output=True, text=True)
    
    if result.returncode != 0:
        # Handle error in listing IPs
        print("Error listing static IPs:", result.stderr)
        return None, None

    addresses = json.loads(result.stdout)
    for address in addresses:
        if address["name"] == formatted_hostname:
            # Return the IP address and the formatted hostname
            return address["address"], formatted_hostname

    # If no static IP, create one
    create_result = subprocess.run(["gcloud", "compute", "addresses", "create", formatted_hostname, "--region", region, "--network-tier", "STANDARD"], capture_output=True, text=True)
    if create_result.returncode != 0:
        # Handle error in creating IP
        print("Error creating static IP:", create_result.stderr)
        return None, None

    new_address_result = subprocess.run(["gcloud", "compute", "addresses", "describe", formatted_hostname, "--region", region, "--format=json"], capture_output=True, text=True)
    if new_address_result.returncode != 0:
        # Handle error in describing new IP
        print("Error describing new static IP:", new_address_result.stderr)
        return None, None

    new_address = json.loads(new_address_result.stdout)
    return new_address["address"], formatted_hostname

def generate_terraform_config(project_id, static_ip, credentials_path):
    formatted_hostname = format_hostname(n8n_hostname)

    config = f"""# Terraform configuration for setting up an instance in GCP
provider "google" {{
    project     = "{project_id}"
    region      = "{region}"
    credentials = "{credentials_path}"
}}
resource "google_compute_instance" "{formatted_hostname}" {{
    name         = "{formatted_hostname}"
    machine_type = "e2-micro"
    zone         = "{region}-a"
    boot_disk {{
        initialize_params {{
            image = "ubuntu-os-cloud/ubuntu-2204-lts"
            size  = 30
        }}
    }}
    network_interface {{
        network = "default"
        access_config {{
            nat_ip = "{static_ip}"
            network_tier = "STANDARD"
        }}
    }}
    metadata = {{
        "ssh-keys" = "{ssh_key}"
    }}

    connection {{
        type        = "ssh"
        user        = "{ssh_user}"
        private_key = file("{ssh_private_key_path}")
        host        = self.network_interface[0].access_config[0].nat_ip
    }}

    # File provisioners to copy setup scripts and docker-compose files to a temporary location
    provisioner "file" {{
        source      = "setup_server.sh"
        destination = "/tmp/setup_server.sh"
    }}
    provisioner "file" {{
        source      = "setup_cloudflare.sh"
        destination = "/tmp/setup_cloudflare.sh"
    }}
    provisioner "file" {{
        source      = "docker-compose.yml"
        destination = "/tmp/docker-compose.yml"
    }}
    provisioner "file" {{
        source      = "docker-compose.service"
        destination = "/tmp/docker-compose.service"
    }}
    provisioner "file" {{
        source      = "updater.sh"
        destination = "/tmp/updater.sh"
    }}
    provisioner "file" {{
        source      = "Dockerfile"
        destination = "/tmp/Dockerfile"
    }}
    provisioner "file" {{
        source      = "docker-entrypoint.sh"
        destination = "/tmp/docker-entrypoint.sh"
    }}

    # Remote-exec provisioner to move files to their final locations and set permissions
    provisioner "remote-exec" {{
        inline = [
            "sudo mv /tmp/setup_server.sh /opt/setup_server.sh",
            "sudo chmod +x /opt/setup_server.sh",
            "sudo mv /tmp/setup_cloudflare.sh /opt/setup_cloudflare.sh",
            "sudo mv /tmp/docker-compose.yml /opt/docker-compose.yml",
            "sudo mv /tmp/docker-compose.service /etc/systemd/system/docker-compose.service",
            "sudo mv /tmp/updater.sh /opt/updater.sh",
            "sudo chmod +x /opt/updater.sh",
            "sudo mv /tmp/Dockerfile /opt/Dockerfile",
            "sudo mv /tmp/docker-entrypoint.sh /opt/docker-entrypoint.sh",
            "sudo chmod +x /opt/docker-entrypoint.sh",
        ]
    }}
}}

output "instance_ip" {{
    value = "{static_ip}"
}}
"""

    with open("setup.tf", "w") as file:
        file.write(config)

def create_file(file_name, content):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, file_name)
    with open(file_path, "w") as file:
        file.write(content)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate n8n setup files")
    parser.add_argument("--no-upload", action="store_true", help="Generate files without uploading to GCP")
    return parser.parse_args()

# Define content for each file
setup_server_content = """#!/bin/bash
# Add Docker's official GPG key
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update apt repositories
sudo apt-get update

# Install Docker
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker service
systemctl start docker
systemctl enable docker

# Pull Docker image for FastAPI
docker pull {fastapi_docker_image}

# Change to the working directory
cd /opt

# Build the custom n8n image
docker build -t custom-n8n:latest .

# Start Docker Compose
sudo docker compose up -d

# Enable Docker Compose service
systemctl enable docker-compose.service

# Create n8n volume directory
sudo mkdir -p /home/{ssh_user}/n8n-local-files

# Create Data Folders and Docker Volumes
sudo docker volume create n8n_data
sudo mkdir -p /home/{ssh_user}/n8n-local-files
""".format(fastapi_docker_image=fastapi_docker_image, ssh_user=ssh_user)

setup_cloudflare_content = """#!/bin/bash
# Add cloudflare gpg key
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
# Add this repo to your apt repositories
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared jammy main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
# install cloudflared
sudo apt-get update && sudo apt-get install cloudflared
sudo cloudflared tunnel login
sudo cloudflared tunnel create {formatted_hostname}
sudo cloudflared tunnel route ip add {static_ip}/32 {formatted_hostname}
sudo cloudflared tunnel route dns {formatted_hostname} {n8n_hostname}
tunnel_id=$(sudo cloudflared tunnel info {formatted_hostname} | grep -oP 'Your tunnel \K([a-z0-9-]+)')
mkdir /etc/cloudflared
echo "tunnel: {formatted_hostname}" > /etc/cloudflared/config.yml
echo "credentials-file: /root/.cloudflared/$tunnel_id.json" >> /etc/cloudflared/config.yml
echo "protocol: quic" >> /etc/cloudflared/config.yml
echo "logfile: /var/log/cloudflared.log" >> /etc/cloudflared/config.yml
echo "loglevel: debug" >> /etc/cloudflared/config.yml
echo "transport-loglevel: info" >> /etc/cloudflared/config.yml
echo "ingress:" >> /etc/cloudflared/config.yml
echo "  - hostname: {n8n_hostname}" >> /etc/cloudflared/config.yml
echo "    service: http://localhost:5678" >> /etc/cloudflared/config.yml
echo "  - service: http_status:404" >> /etc/cloudflared/config.yml
cloudflared service install
systemctl start cloudflared
systemctl status cloudflared
""".format(formatted_hostname=format_hostname(n8n_hostname), static_ip="<STATIC_IP>", n8n_hostname=n8n_hostname)

docker_compose_content = """version: '3'
services:
  n8n:
    build: .
    user: "node"
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST={n8n_hostname}
      - WEBHOOK_URL={webhook_url}
      - NODE_FUNCTION_ALLOW_EXTERNAL=socket.io,socket.io-client
    restart: unless-stopped
    volumes:
      - n8n_data:/home/node/.n8n
      - /home/{ssh_user}/n8n-local-files:/data/files
  fastapi:
    image: {fastapi_docker_image}
    ports:
      - "8000:8000"
    restart: unless-stopped
volumes:
  n8n_data:
""".format(ssh_user=ssh_user, fastapi_docker_image=fastapi_docker_image, n8n_hostname=n8n_hostname, webhook_url=webhook_url)

docker_compose_service_content = """[Unit]
Description=Docker Compose Application Service
Requires=docker.service
After=docker.service

[Service]
Type=simple
WorkingDirectory=/opt
ExecStart=docker compose -f /opt/docker-compose.yml up
ExecStop=docker compose -f /opt/docker-compose.yml down
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
"""

updater_content = """#!/bin/bash
# Update the package index
sudo apt update

# Upgrade Docker and Cloudflared
sudo apt upgrade docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin cloudflared

# Pull the latest base image for n8n
docker pull n8nio/n8n:latest

# Pull the latest docker image for FastAPI
docker pull {fastapi_docker_image}

# Build the custom n8n image based on the latest base image
docker build -t custom-n8n:latest /opt

# Stop current setup
sudo docker compose stop

# Delete docker containers (data is stored separately)
sudo docker compose rm -f

# Start Docker again, using the updated custom image
sudo docker compose -f /opt/docker-compose.yml up -d --build
""".format(fastapi_docker_image=fastapi_docker_image)

dockerfile_content = """# Use the n8n base image
FROM n8nio/n8n:latest

# Switch to root user to install global npm packages
USER root

# Install socket.io-client globally
RUN npm install -g socket.io-client

# Switch back to the node user
USER node

# Set working directory to avoid potential errors
WORKDIR /data

# Copy the custom entrypoint script to the container
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /docker-entrypoint.sh

# Use the custom entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

# Expose the port n8n uses
EXPOSE 5678
"""

docker_entrypoint_content = """#!/bin/sh

# Ensure the /data directory and /home/node/.n8n directory exist
mkdir -p /data /home/node/.n8n

# Ensure the node user owns these directories
chown -R node:node /data /home/node/.n8n

exec n8n "$@"
"""

def main():
    args = parse_arguments()

    if args.no_upload:
        # Generate client-side template files only
        create_file("setup_server.sh", setup_server_content)
        create_file("setup_cloudflare.sh", setup_cloudflare_content)
        create_file("docker-compose.yml", docker_compose_content)
        create_file("docker-compose.service", docker_compose_service_content)
        create_file("updater.sh", updater_content)
        create_file("Dockerfile", dockerfile_content)
        create_file("docker-entrypoint.sh", docker_entrypoint_content)
        print("Client-side template files generated successfully.")
    else:
        # Perform full setup including GCP operations
        project_id = fetch_project_id()
        credentials_path = fetch_service_account_key()
        static_ip, formatted_hostname = check_static_ip(n8n_hostname, region)

        if static_ip is None or formatted_hostname is None:
            print("Error: Unable to obtain static IP or formatted hostname.")
            sys.exit(1)

        create_file("setup_server.sh", setup_server_content)
        create_file("setup_cloudflare.sh", setup_cloudflare_content.format(static_ip=static_ip))
        create_file("docker-compose.yml", docker_compose_content)
        create_file("docker-compose.service", docker_compose_service_content)
        create_file("updater.sh", updater_content)
        create_file("Dockerfile", dockerfile_content)
        create_file("docker-entrypoint.sh", docker_entrypoint_content)
        generate_terraform_config(project_id, static_ip, credentials_path)
        print("All files generated and Terraform configuration created successfully.")

if __name__ == "__main__":
    main()
