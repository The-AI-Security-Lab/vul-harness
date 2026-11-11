output "deployment_id" {
  value = var.deployment_id
}

output "expires_at" {
  value = var.expires_at
}

output "vpc_id" {
  value = aws_vpc.lab.id
}

output "subnet_id" {
  value = aws_subnet.public.id
}

output "security_group_id" {
  value = aws_security_group.lab.id
}

output "lab_c_instance_id" {
  value = aws_instance.lab_c.id
}

output "lab_d_instance_id" {
  value = aws_instance.lab_d.id
}
