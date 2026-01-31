#!/bin/bash
#
# Quick connect to Paper Trading EC2 instance
# Usage: ./connect.sh [instance-name]
#

INSTANCE_NAME=${1:-paper-trading-bot}
KEY_FILE="paper-trading-key.pem"

# Find instance IP by name
echo "Finding instance: $INSTANCE_NAME..."

PUBLIC_IP=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=$INSTANCE_NAME" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

if [ -z "$PUBLIC_IP" ] || [ "$PUBLIC_IP" = "None" ]; then
    echo "ERROR: Could not find running instance named '$INSTANCE_NAME'"
    echo ""
    echo "Running instances:"
    aws ec2 describe-instances \
        --filters "Name=instance-state-name,Values=running" \
        --query 'Reservations[].Instances[].[Tags[?Key==`Name`].Value|[0],PublicIpAddress]' \
        --output table
    exit 1
fi

echo "Connecting to $PUBLIC_IP..."
ssh -i "$KEY_FILE" ubuntu@"$PUBLIC_IP"
