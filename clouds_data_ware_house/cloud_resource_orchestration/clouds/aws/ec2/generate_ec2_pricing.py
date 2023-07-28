
import os
from ec2_pricing import EC2Pricing

# Access environment variables using os.environ
output_path = os.environ.get('OUTPUT_PATH', '')

ec2_pricing = EC2Pricing(output_path=output_path)
ec2_pricing.ec2_spot_prices()
ec2_pricing.ec2_on_demand_prices()
