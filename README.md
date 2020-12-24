# Cloud Governance
This tool provides an engineer with a lightweight and flexible framework for 
deploying cloud management policies and controls at scale.

**General**

* policies: The policies that run by cloud custodian tool
* cluster_tags: Script that update cluster tags according to cluster name
* zombie_cluster: find zombie cluster in account

TBD:
* The cloud-governance package is placed in [PyPi](TBD)
* The cloud-governance pipeline is placed in [Jenkins](TBD)



How to install?
need to run it as root
```bash
aws configure
git clone https://github.com/redhat-performance/cloud-governance
python3 -m venv governance
python -m pip install --upgrade pip
pip3 install wheel
source governance/bin/activate
pip3 install /cloud-governance/cloud_governance-1.0.0-py3-none-any.whl
python3
>> from cloud_governance.zombie_cluster import run_zombie_cluster_resources
>> run_zombie_cluster_resources.zombie_cluster_resource()
>> run_zombie_cluster_resources.delete_zombie_cluster_resource()
```

How to run pytest?
```bash
coverage run -m pytest
```
