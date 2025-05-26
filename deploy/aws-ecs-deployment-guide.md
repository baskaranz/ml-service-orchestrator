# AWS ECS Deployment Guide

This guide provides step-by-step instructions for deploying the ML Service Orchestrator to AWS ECS (Elastic Container Service).

## Prerequisites

1. AWS CLI installed and configured with appropriate permissions
2. AWS ECR repository created for the application
3. Docker installed locally
4. ECS CLI installed and configured (optional but recommended)
5. Required AWS resources (VPC, ECS Cluster, etc.)

## 1. Environment Setup

### 1.1 Directory Structure

Create the following directory structure for environment-specific configurations:

```
config/
  ├── dev/
  │   └── models/
  ├── stg/
  │   └── models/
  └── prod/
      └── models/
```

### 1.2 Environment Variables

Create environment files for each environment (e.g., `.env.dev`, `.env.stg`, `.env.prod`) with the following variables:

```env
# Application
ENVIRONMENT=prod
LOG_LEVEL=INFO
PORT=8000

# AWS
AWS_REGION=ap-southeast-2
AWS_ACCOUNT_ID=your-account-id
ECR_REPOSITORY=ml-orchestrator

# ECS
ECS_CLUSTER=ml-orchestrator-cluster
ECS_SERVICE=ml-orchestrator-service
TASK_DEFINITION=ml-orchestrator-task
CONTAINER_NAME=ml-orchestrator

# Load Balancer (if using)
ALB_SECURITY_GROUP=sg-xxxxxxxx
ALB_TARGET_GROUP_ARN=arn:aws:elasticloadbalancing:...

# VPC
VPC_ID=vpc-xxxxxxxx
SUBNET_IDS=subnet-xxxxxxxx,subnet-yyyyyyyy
SECURITY_GROUP_IDS=sg-xxxxxxxx
```

## 2. Build and Push Docker Image

### 2.1 Build the Docker Image

```bash
# Build for development
./scripts/build.sh dev

# Build for staging
./scripts/build.sh stg

# Build for production
./scripts/build.sh prod
```

### 2.2 Push to ECR

```bash
# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag and push the image
./scripts/push.sh <environment>
```

## 3. Infrastructure as Code (Terraform)

### 3.1 Create Terraform Configuration

Create a `terraform` directory with the following structure:

```
terraform/
  ├── main.tf
  ├── variables.tf
  ├── outputs.tf
  └── environments/
      ├── dev.tfvars
      ├── stg.tfvars
      └── prod.tfvars
```

### 3.2 Example Terraform Configuration

```hcl
# main.tf
provider "aws" {
  region = var.aws_region
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-cluster-${var.environment}"
}

# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.app_name}-task-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name         = var.container_name
      image        = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
      essential    = true
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "LOG_LEVEL", value = var.log_level }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/${var.app_name}-${var.environment}"
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

# ECS Service
resource "aws_ecs_service" "main" {
  name            = "${var.app_name}-service-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups = [aws_security_group.ecs_tasks.id]
    subnets         = var.private_subnets
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.id
    container_name   = var.container_name
    container_port   = var.container_port
  }
}
```

## 4. Deployment Scripts

### 4.1 Build Script (`scripts/build.sh`)

```bash
#!/bin/bash
set -e

ENVIRONMENT=${1:-dev}
IMAGE_TAG=${2:-latest}

if [[ ! "$ENVIRONMENT" =~ ^(dev|stg|prod)$ ]]; then
    echo "Environment must be one of: dev, stg, prod"
    exit 1
fi

# Build the Docker image
docker build \
    --build-arg ENVIRONMENT=$ENVIRONMENT \
    -t $ECR_REPOSITORY:$ENVIRONMENT-$IMAGE_TAG \
    -t $ECR_REPOSITORY:$ENVIRONMENT-latest \
    .

echo "Successfully built $ECR_REPOSITORY:$ENVIRONMENT-$IMAGE_TAG"
```

### 4.2 Push Script (`scripts/push.sh`)

```bash
#!/bin/bash
set -e

ENVIRONMENT=${1:-dev}
IMAGE_TAG=${2:-latest}

if [[ ! "$ENVIRONMENT" =~ ^(dev|stg|prod)$ ]]; then
    echo "Environment must be one of: dev, stg, prod"
    exit 1
fi

# Get the account number associated with the current IAM credentials
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ $? -ne 0 ]; then
    exit 255
fi

# ECR repository name
ECR_REPOSITORY=ml-orchestrator

# AWS region
REGION=$(aws configure get region)
REGION=${REGION:-ap-southeast-2}  # Default to Sydney if not set

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Tag and push the image
for tag in {$ENVIRONMENT-$IMAGE_TAG,$ENVIRONMENT-latest}; do
    docker tag $ECR_REPOSITORY:$tag $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:$tag
    docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:$tag
    echo "Successfully pushed $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:$tag"
done
```

### 4.3 Deploy Script (`scripts/deploy.sh`)

```bash
#!/bin/bash
set -e

ENVIRONMENT=${1:-dev}
IMAGE_TAG=${2:-latest}

if [[ ! "$ENVIRONMENT" =~ ^(dev|stg|prod)$ ]]; then
    echo "Environment must be one of: dev, stg, prod"
    exit 1
fi

# Source environment variables
source .env.$ENVIRONMENT

# Update ECS service
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --task-definition $(aws ecs register-task-definition \
        --cli-input-json file://task-definition-$ENVIRONMENT.json \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text) \
    --force-new-deployment

echo "Deployment initiated for $ENVIRONMENT environment with image tag $IMAGE_TAG"
```

## 5. CI/CD Pipeline (GitHub Actions)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to ECS

on:
  push:
    branches:
      - main
    paths:
      - 'app/**'
      - 'config/**'
      - 'Dockerfile'
      - 'requirements.txt'
      - '.github/workflows/deploy.yml'

env:
  AWS_REGION: ap-southeast-2
  ECR_REPOSITORY: ml-orchestrator
  ECS_SERVICE: ml-orchestrator-service
  ECS_CLUSTER: ml-orchestrator-cluster
  CONTAINER_NAME: ml-orchestrator

jobs:
  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    environment: production

    steps:
    - name: Checkout
      uses: actions/checkout@v3

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1

    - name: Build, tag, and push image to Amazon ECR
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: ${{ env.ECR_REPOSITORY }}
        IMAGE_TAG: ${{ github.sha }}
      run: |
        # Build and tag the image
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest

        # Push the image
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest

        # Store the image tag for the deploy step
        echo "IMAGE_TAG=$IMAGE_TAG" >> $GITHUB_ENV

    - name: Deploy to ECS
      env:
        ECS_SERVICE: ${{ env.ECS_SERVICE }}
        ECS_CLUSTER: ${{ env.ECS_CLUSTER }}
        ECR_REPOSITORY: ${{ env.ECR_REPOSITORY }}
        CONTAINER_NAME: ${{ env.CONTAINER_NAME }}
      run: |
        # Update the ECS service with the new task definition
        aws ecs update-service \
          --cluster $ECS_CLUSTER \
          --service $ECS_SERVICE \
          --force-new-deployment \
          --query "service.serviceArn"
```

## 6. Monitoring and Logging

### 6.1 CloudWatch Logs

All container logs are automatically sent to CloudWatch Logs. You can view them in the AWS Management Console or use the AWS CLI:

```bash
# Get the most recent log events
aws logs get-log-events \
  --log-group-name "/ecs/ml-orchestrator-prod" \
  --log-stream-name "ecs/ml-orchestrator-container/container-id" \
  --limit 50
```

### 6.2 CloudWatch Alarms

Set up CloudWatch Alarms for:
- CPU utilization > 70%
- Memory utilization > 80%
- Number of running tasks < 1

## 7. Rollback Procedure

### 7.1 Manual Rollback

```bash
# Get previous task definition
PREVIOUS_TASK_DEF=$(aws ecs describe-services \
  --cluster $ECS_CLUSTER \
  --services $ECS_SERVICE \
  --query 'services[0].deployments[?status==\'PRIMARY\'].taskDefinition' \
  --output text | awk -F'/' '{print $2}' | awk -F':' '{print $1}')

# Update service to use previous task definition
aws ecs update-service \
  --cluster $ECS_CLUSTER \
  --service $ECS_SERVICE \
  --task-definition $PREVIOUS_TASK_DEF \
  --force-new-deployment
```

## 8. Security Best Practices

1. **Secrets Management**:
   - Store sensitive configuration in AWS Secrets Manager or Parameter Store
   - Use IAM roles for ECS tasks instead of hardcoded credentials

2. **Network Security**:
   - Use security groups to restrict traffic to only necessary ports
   - Place ECS tasks in private subnets
   - Use VPC endpoints for AWS services to avoid public internet traffic

3. **Container Security**:
   - Regularly scan container images for vulnerabilities
   - Run containers as non-root users
   - Keep your base images updated

## 9. Cost Optimization

1. **Right-size your tasks**:
   - Monitor CPU and memory usage and adjust task definitions accordingly
   - Use AWS Compute Optimizer for recommendations

2. **Auto Scaling**:
   - Implement Application Auto Scaling based on CPU/Memory utilization
   - Use scheduled scaling for predictable traffic patterns

3. **Spot Instances**:
   - Use Fargate Spot for non-critical workloads to save costs

## 10. Troubleshooting

### Common Issues:

1. **Task fails to start**:
   - Check CloudWatch logs for error messages
   - Verify that the container can pull the image from ECR
   - Check task execution role permissions

2. **High latency**:
   - Check CloudWatch metrics for CPU/Memory usage
   - Review application logs for slow queries or operations
   - Consider enabling AWS X-Ray for distributed tracing

3. **Service not reachable**:
   - Verify security group rules
   - Check load balancer target group health checks
   - Verify that the container is listening on the correct port

## Support

For any issues, please contact the DevOps team or create an issue in the repository.
