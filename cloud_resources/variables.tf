variable "thumbprint_list" {
  type = list(string)
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "url" {
  type = string
}

variable "github_token" {
  description = "GitHub Personal Access Token"
  type        = string
}

variable "repo_owner" {
  description = "GitHub Repository Owner"
  type        = string
}

variable "repo_name" {
  description = "GitHub Repository Name"
  type        = string
}
