# Security Group
resource "aws_security_group" "cleanup_test_sg" {
  name        = "cleanup-test-sg"
  description = "Allow SSH access"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# # Key Pair for EC2 Access
# resource "aws_key_pair" "cleanup_test_key" {
#   key_name   = "cleanup-key"
#   public_key = file("~/.ssh/id_rsa.pub")
# }

# EC2 Instances
resource "aws_instance" "instances" {
  for_each = {
    idle_monitoring_disabled = {
      name       = "IdleInstance-MonitoringDisabled"
      monitoring = false
      user_data  = null
    }
    low_cpu_utilization = {
      name       = "IdleInstance-LowCPUUtilization"
      monitoring = true
      user_data  = <<EOF
          #!/bin/bash
          # Simulate low CPU utilization by running a lightweight process
          while true; do sleep 60; done
      EOF
    }
  }

  ami             = "ami-0c02fb55956c7d316" # Amazon Linux 2 AMI
  instance_type   = "t2.micro"
  key_name        = "my-ec2-key"
  security_groups = [aws_security_group.cleanup_test_sg.name]
  monitoring      = each.value.monitoring

  tags = {
    Name        = each.value.name
    Environment = "Test"
  }

  user_data = each.value.user_data
}

# EBS Volumes
resource "aws_ebs_volume" "unattached_volumes" {
  for_each = {
    volume1 = { name = "UnattachedVolume1", az = "${var.region}a" }
    volume2 = { name = "UnattachedVolume2", az = "${var.region}a" }
  }
  availability_zone = each.value.az
  size              = 10
  tags = {
    Name        = each.value.name
    Environment = "Test"
  }
}
