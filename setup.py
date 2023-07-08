from codecs import open
from os import path
from setuptools import setup, find_packages

__version__ = '1.1.128'

here = path.abspath(path.dirname(__file__))

if path.isfile(path.join(here, 'README.md')):
    with open(path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
else:
    long_description = ""

setup(
    name='cloud-governance',
    version=__version__,
    description='Cloud Governance Tool',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Red Hat',
    author_email='ebattat@redhat.com, athiruma@redhat.com',
    url='https://github.com/redhat-performance/cloud-governance',
    license="Apache License 2.0",
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],

    zip_safe=False,

    # Find all packages (__init__.py)
    packages=find_packages(include=['cloud_governance', 'cloud_governance.*']),

    install_requires=[
        'aiohttp==3.8.1',  # required by jira
        'attrs==21.4.0',  # readthedocs
        'azure-identity==1.12.0',  # azure identity
        'azure-mgmt-billing==6.0.0',  # azure billing management
        'azure-mgmt-costmanagement==3.0.0',  # azure cost management
        'azure-mgmt-subscription==3.1.1',  # azure subscriptions
        'boto3==1.26.1',  # required by c7n 0.9.14
        'botocore==1.29.1',  # required by c7n 0.9.14
        'elasticsearch-dsl==7.4.0',
        'elasticsearch==7.11.0',  # depend on elasticsearch server
        'google-api-python-client==2.57.0',  # google drive
        'google-auth-httplib2==0.1.0',  # google drive
        'google-auth-oauthlib==0.5.2',  # google drive
        'google-cloud-bigquery==3.5.0',  # google cloud cost
        'google-cloud-billing==1.9.1',  # google cloud cost
        'ibm_platform_services==0.27.0',  # IBM Usage reports
        'myst-parser==0.17.0',  # readthedocs
        'oauthlib~=3.1.1',  # required by jira
        'pandas',  # latest: aggregate ec2/ebs cluster data
        'PyGitHub==1.55',  # gitleaks
        'python-ldap==3.4.2',  # prerequisite: sudo dnf install -y python39-devel openldap-devel gcc
        'requests==2.31.0',  # rest api & lambda
        'retry==0.9.2',
        'SoftLayer==6.0.0',  # IBM SoftLayer
        'sphinx-rtd-theme==1.0.0',  # readthedocs
        'sphinx==4.5.0',  # readthedocs
        'typeguard==2.13.3',  # checking types
        'typing==3.7.4.3',
        'urllib3==1.26.7',  # required by jira

    ],

    setup_requires=['pytest', 'pytest-runner', 'wheel', 'coverage'],

    include_package_data=True,

    # dependency_links=[]
)
