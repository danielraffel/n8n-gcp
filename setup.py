import subprocess
import json
import os

# Global variables
n8n_hostname = "n8n.YOURDOMAIN.COM" # Required. Example: n8n.generouscorp.com
webhook_url = f"https://{n8n_hostname}/"
fastapi_docker_image = "tiangolo/uvicorn-gunicorn-fastapi:python3.11"
region = "us-west1"
ssh_key = "user_name:ssh-rsa string" # Required. Example: service_account:ssh-rsa SDqhy5jXUv3xKGhzYJzjALiHg6ZzWKSSrhbjXVAvp6SecWdZPkGw16UhHHTCHvD4bwjnH6NXjHtyuCVqhdDuY1+E1BSdf0G0rncN8qFrzT1imJqraru38UEJRTZFrXMG6Kvx698J[ELvapEXXMv52zW6ZwHuU5aJ0t2atDHEXha7V3UAKSbgxLbbtQGRgtANcz3fvk9ve8GVPEtB3Cyz3eyg4aBHVqLyxx3N9hithMe

def fetch_project_id():
    # Fetch project ID using Google Cloud CLI
    result = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
    return result.stdout.strip()

def fetch_service_account_key(project_id):
    # Fetch service account details
    accounts = subprocess.run(["gcloud", "iam", "service-accounts", "list", "--format=json"], capture_output=True, text=True)
    accounts_json = json.loads(accounts.stdout)
    
    # Assuming the first account is the default service account
    default_service_account = accounts_json[0]["email"]

    # Creating a service account key
    key_filename = f"{project_id}-key.json"
    subprocess.run(["gcloud", "iam", "service-accounts", "keys", "create", key_filename, "--iam-account", default_service_account])

    # Rename the key file to something generic
    generic_key_filename = "service-account-key.json"
    os.rename(key_filename, generic_key_filename)
    return generic_key_filename

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
        return None

    addresses = json.loads(result.stdout)
    for address in addresses:
        if address["name"] == formatted_hostname and address["status"] == "RESERVED":
            return address["address"]

    # If no static IP, create one in the same region as the VM instance
    create_result = subprocess.run(["gcloud", "compute", "addresses", "create", formatted_hostname, "--region", region, "--network-tier", "STANDARD"], capture_output=True, text=True)
    if create_result.returncode != 0:
        # Handle error in creating IP
        print("Error creating static IP:", create_result.stderr)
        return None

    new_address_result = subprocess.run(["gcloud", "compute", "addresses", "describe", formatted_hostname, "--region", region, "--format=json"], capture_output=True, text=True)
    if new_address_result.returncode != 0:
        # Handle error in describing new IP
        print("Error describing new static IP:", new_address_result.stderr)
        return None

    new_address = json.loads(new_address_result.stdout)
    return new_address["address"]

def check_firewall_rule(project_id, rule_name):
    # Check if the firewall rule exists
    result = subprocess.run(["gcloud", "compute", "firewall-rules", "describe", rule_name, "--project", project_id], capture_output=True)
    return result.returncode == 0

def generate_terraform_config(project_id, static_ip, credentials_path):
    formatted_hostname = format_hostname(n8n_hostname)

    # Check if the firewall rule for port 5678 exists
    firewall_rule_exists = check_firewall_rule(project_id, "allow-n8n-port")

    # Conditional configuration for firewall rule
    firewall_config = ""
    if not firewall_rule_exists:
        firewall_config = '''
        # Firewall rule to allow traffic on port 5678
        resource "google_compute_firewall" "allow_n8n_port" {
            name    = "allow-n8n-port"
            network = "default"
            allow {
                protocol = "tcp"
                ports    = ["5678"]
            }
            source_ranges = ["0.0.0.0/0"]
        }
        '''

    config = f"""
    # Terraform configuration for setting up an instance in GCP
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
                size  = 60
            }}
        }}
        network_interface {{
            network = "default"
            access_config {{
                nat_ip = "{static_ip}"
                network_tier = "STANDARD"
            }}
        }}

        # Create setup server script to install Docker, n8n and FastAPI
        metadata_startup_script = <<-EOT
        cat <<EOSS > /opt/setup_server.sh
        #!/bin/bash
        apt update
        apt -y install docker.io apache2 wget
        systemctl start docker
        systemctl enable docker
        docker pull {fastapi_docker_image}
        docker run -d -p 8000:8000 {fastapi_docker_image}
        docker pull n8nio/n8n
        docker run -d -p 5678:5678 --env N8N_HOST="{n8n_hostname}" --env WEBHOOK_URL="https://{n8n_hostname}/" n8nio/n8n
        # Install Docker Compose
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.3/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        # Verify installation
        echo "Docker Compose version:"
        /usr/local/bin/docker-compose --version
        EOSS
        
        # Create docker-compose.yml
        cat <<EODC > /opt/docker-compose.yml
        version: '1'
        services:
          n8n:
            image: n8nio/n8n
            ports:
              - "5678:5678"
            environment:
              - N8N_HOST={n8n_hostname}
              - WEBHOOK_URL={webhook_url}
            restart: unless-stopped
          fastapi:
            image: {fastapi_docker_image}
            ports:
              - "8000:8000"
            restart: unless-stopped
        EODC

        # Create docker-compose service file
        cat <<EDCS > /etc/systemd/system/docker-compose.service
        [Unit]
        Description=Docker Compose Application Service
        Requires=docker.service
        After=docker.service

        [Service]
        Type=simple
        WorkingDirectory=/opt
        ExecStart=/usr/local/bin/docker-compose -f /opt/docker-compose.yml up
        ExecStop=/usr/local/bin/docker-compose -f /opt/docker-compose.yml down
        Restart=always
        RestartSec=5s

        [Install]
        WantedBy=multi-user.target
        EDCS

        systemctl daemon-reload
        systemctl enable docker-compose.service
        systemctl start docker-compose.service
        EOF
        chmod +x /opt/setup_server.sh

        # Cloudflare setup script
        cat <<EOCF > /opt/setup_cloudflare.sh
        #!/bin/bash
        wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
        mv ./cloudflared-linux-amd64 /usr/local/bin/cloudflared
        chmod a+x /usr/local/bin/cloudflared
        cloudflared update
        sudo cloudflared tunnel login
        sudo cloudflared tunnel create {formatted_hostname}
        sudo cloudflared tunnel route ip add {static_ip}/32 {formatted_hostname}
        sudo cloudflared tunnel route dns {formatted_hostname} {n8n_hostname}
        tunnel_id=\$(sudo cloudflared tunnel info {formatted_hostname} | grep -oP 'Your tunnel \K([a-z0-9-]+)')
        mkdir /etc/cloudflared
        echo "tunnel: {formatted_hostname}" > /etc/cloudflared/config.yml
        echo "credentials-file: /root/.cloudflared/\$tunnel_id.json" >> /etc/cloudflared/config.yml
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
        EOCF
        chmod +x /opt/setup_cloudflare.sh
        EOT

        metadata = {{
            "ssh-keys" = "{ssh_key}"
        }}
    }}

    output "instance_ip" {{
        value = "{static_ip}"
    }}
    {firewall_config}
    """

    with open("setup.tf", "w") as file:
        file.write(config)

# Fetch project ID
project_id = fetch_project_id()

# Download service account key and get the path
credentials_path = fetch_service_account_key(project_id)

# Check for an existing static IP or create a new one
static_ip = check_static_ip(n8n_hostname, region)

# Generate Terraform configuration
generate_terraform_config(project_id, static_ip, credentials_path)
