LOOK_BACK_DAYS = 30
MONTHS = 12
DEFAULT_ROUND_DIGITS = 3
PUBLIC_ACCOUNTS_COST_REPORTS = 'Accounts'
IT_ACCOUNTS_COST_REPORTS_LIST = 'IT_ACCOUNTS'
HOURS_IN_SECONDS = 3600
HOURS_IN_DAY = 24
HOURS_IN_MONTH = 720
TOTAL_BYTES_IN_KIB = 1024

DATE_FORMAT = "%Y-%m-%d"
DATE_TIME_FORMAT_T = "%Y-%m-%dT%h:%m"
UNUSED_DAYS = 7

# Policy Values
# Instance Idle
INSTANCE_IDLE_DAYS = 7
INSTANCE_IDLE_CPU_PERCENTAGE = 2
INSTANCE_IDLE_NETWORK_IN_KILO_BYTES = 5  # In KiB
INSTANCE_IDLE_NETWORK_OUT_KILO_BYTES = 5  # In KiB
EC2_NAMESPACE = 'AWS/EC2'
CLOUDWATCH_METRICS_AVAILABLE_DAYS = 14
AWS_DEFAULT_GLOBAL_REGION = 'us-east-1'

# X86 to Graviton
GRAVITON_MAPPINGS = {
    'c6a': 'c6g',
    'c6i': 'c6g',
    'c6in': 'c6gn',
    'c7': 'c7g',
    'c7i': 'c7g',
    'c7a': 'c7g',
    'c7i-flex': 'c7g',
    'g5': 'g5g',
    'hpc7a': 'hpc7g',
    'i4i': 'i4g',
    'm5': 'm6g',
    'm5a': 'm6g',
    'm5n': 'm6g',
    'm5zn': 'm6g',
    'm6i': 'm6g',
    'm6in': 'm6g',
    'm6a': 'm6g',
    'm7i': 'm7g',
    'm7a': 'm7g',
    'm7i-flex': 'm7g',
    'r7i': 'r8g',
    'r7a': 'r7g',
    'r5': 'r7g',
    'r6i': 'r6g',
    't3': 't4g',
    't2': 'a1'
}

DEFAULT_GRAVITON_INSTANCE = 'm6g'
