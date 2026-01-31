#!/bin/bash
#
# Launch EC2 Instance for Paper Trading Bot
# Run from your local machine with AWS CLI configured
#
# Usage: ./launch-ec2.sh [instance-type]
# Example: ./launch-ec2.sh t3.small
#

set -e

INSTANCE_TYPE=${1:-t3.small}
KEY_NAME="paper-trading-key"
SECURITY_GROUP_NAME="paper-trading-sg"
INSTANCE_NAME="paper-trading-bot"

# Ubuntu 24.04 LTS AMI IDs (us-east-1)
# Update these for your region
AMI_ID="ami-0c7217cdde317cfec"

echo "=============================================="
echo "Launching Paper Trading Bot EC2 Instance"
echo "=============================================="
echo ""
echo "Instance Type: $INSTANCE_TYPE"
echo "Region: $(aws configure get region)"
echo ""

# Check if key pair exists
echo "[1/5] Checking key pair..."
if ! aws ec2 describe-key-pairs --key-names "$KEY_NAME" &>/dev/null; then
    echo "Creating key pair: $KEY_NAME"
    aws ec2 create-key-pair \
        --key-name "$KEY_NAME" \
        --query 'KeyMaterial' \
        --output text > "${KEY_NAME}.pem"
    chmod 400 "${KEY_NAME}.pem"
    echo "Key pair saved to ${KEY_NAME}.pem"
else
    echo "Key pair already exists"
fi

# Check/create security group
echo "[2/5] Checking security group..."
SG_ID=$(aws ec2 describe-security-groups \
    --group-names "$SECURITY_GROUP_NAME" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "")

if [ -z "$SG_ID" ] || [ "$SG_ID" = "None" ]; then
    echo "Creating security group: $SECURITY_GROUP_NAME"
    SG_ID=$(aws ec2 create-security-group \
        --group-name "$SECURITY_GROUP_NAME" \
        --description "Paper Trading Bot Security Group" \
        --query 'GroupId' \
        --output text)

    # Allow SSH from anywhere (you may want to restrict this)
    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0

    echo "Security group created: $SG_ID"
else
    echo "Security group already exists: $SG_ID"
fi

# Create user data script
echo "[3/5] Preparing user data..."
USER_DATA=$(cat << 'EOF'
#!/bin/bash
# Auto-setup on first boot
cd /home/ubuntu
sudo -u ubuntu bash << 'INNER'
curl -fsSL https://raw.githubusercontent.com/hyperliquid-dex/hyperliquid-python-sdk/master/infra/scripts/setup-ec2.sh | bash
INNER
EOF
)

# Launch instance
echo "[4/5] Launching instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "Instance launched: $INSTANCE_ID"

# Wait for instance to be running
echo "[5/5] Waiting for instance to start..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo ""
echo "=============================================="
echo "Instance Ready!"
echo "=============================================="
echo ""
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo ""
echo "Connect with:"
echo "  ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP"
echo ""
echo "Wait ~2 minutes for initial setup, then:"
echo "  1. SSH into the instance"
echo "  2. Edit credentials: nano ~/hyperliquid-python-sdk/.env"
echo "  3. Login to Claude: claude login"
echo "  4. Start the bot: sudo systemctl start paper-trading"
echo ""
