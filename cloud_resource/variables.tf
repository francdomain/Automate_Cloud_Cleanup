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
