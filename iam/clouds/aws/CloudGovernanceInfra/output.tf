output "SECRET_KEY_ID" {
  value     = module.CreateIAMInfra.SECRET_KEY_ID
  sensitive = true
}

output "ACCESS_KEY_ID" {
  value = module.CreateIAMInfra.ACCESS_KEY_ID
}
