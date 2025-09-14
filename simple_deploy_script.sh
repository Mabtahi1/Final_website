#!/bin/bash

# Simple AWS ECS Deployment for Prolexis Analytics Platform
# Run: chmod +x deploy.sh && ./deploy.sh

set -e

# Configuration - UPDATE THESE
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="YOUR_AWS_ACCOUNT_ID"
APP_NAME="prolexis-platform"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 Deploying Prolexis Analytics Platform${NC}"

# Step 1: Create ECR repository
echo -e "${YELLOW}📦 Creating ECR repository...${NC}"
aws ecr create-repository \
    --repository-name $APP_NAME \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true || echo "Repository exists"

# Step 2: Login to ECR
echo -e "${YELLOW}🔐 Logging into ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Step 3: Build and push image
echo -e "${YELLOW}🏗️ Building Docker image...${NC}"
docker build -t $APP_NAME .

echo -e "${YELLOW}📤 Pushing to ECR...${NC}"
docker tag $APP_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$APP_NAME:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$APP_NAME:latest

# Step 4: Create/update ECS resources
echo -e "${YELLOW}☁️ Setting up ECS resources...${NC}"

# Create cluster
aws ecs create-cluster \
    --cluster-name $APP_NAME-cluster \
    --capacity-providers FARGATE \
    --region $AWS_REGION || echo "Cluster exists"

# Create task definition
cat > task-definition.json << EOF
{
  "family": "$APP_NAME-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "$APP_NAME",
      "image": "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$APP_NAME:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "FLASK_ENV",
          "value": "production"
        },
        {
          "name": "PORT",
          "value": "5000"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$APP_NAME",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      },
      "essential": true
    }
  ]
}
EOF

# Register task definition
aws ecs register-task-definition \
    --cli-input-json file://task-definition.json \
    --region $AWS_REGION

# Get default VPC and subnets
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text | tr '\t' ',')

# Create security group
SG_ID=$(aws ec2 create-security-group \
    --group-name $APP_NAME-sg \
    --description "Security group for $APP_NAME" \
    --vpc-id $VPC_ID \
    --query 'GroupId' \
    --output text 2>/dev/null || \
    aws ec2 describe-security-groups --filters "Name=group-name,Values=$APP_NAME-sg" --query 'SecurityGroups[0].GroupId' --output text)

# Add security group rules
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 5000 \
    --cidr 0.0.0.0/0 || echo "Rule exists"

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 || echo "Rule exists"

# Create/update service
aws ecs create-service \
    --cluster $APP_NAME-cluster \
    --service-name $APP_NAME-service \
    --task-definition $APP_NAME-task \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
    --region $AWS_REGION || \
    aws ecs update-service \
        --cluster $APP_NAME-cluster \
        --service $APP_NAME-service \
        --task-definition $APP_NAME-task \
        --region $AWS_REGION

# Cleanup
rm task-definition.json

echo -e "${GREEN}✅ Deployment completed!${NC}"
echo -e "${GREEN}Your app is deploying on ECS Fargate${NC}"
echo -e "${YELLOW}To get the public IP:${NC}"
echo "aws ecs describe-tasks --cluster $APP_NAME-cluster --tasks \$(aws ecs list-tasks --cluster $APP_NAME-cluster --service-name $APP_NAME-service --query 'taskArns[0]' --output text) --query 'tasks[0].attachments[0].details[?name==\`networkInterfaceId\`].value' --output text | xargs -I {} aws ec2 describe-network-interfaces --network-interface-ids {} --query 'NetworkInterfaces[0].Association.PublicIp' --output text"