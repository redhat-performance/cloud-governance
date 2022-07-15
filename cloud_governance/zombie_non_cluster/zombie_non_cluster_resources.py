import boto3

from cloud_governance.common.aws.ec2.ec2_operations import EC2Operations


class ZombieNonClusterResources:

    def __init__(self, region: str = 'us-east-2', dry_run: str = 'yes'):
        self.dry_run = dry_run
        self.region = region
        self.__ec2_client = boto3.client('ec2', region_name=self.region)
        self.__ec2_operations = EC2Operations(region=self.region)

    def __get_image_ids_from_description(self, snapshot_description: str):
        """
        This method gets image Ids from snapshot description
        Two cases:
        # Created by CreateImage(i-******) for ami-********
        # Copied for DestinationAmi ami-******* from SourceAmi ami-******* for SourceSnapshot snap-******. Task created on 1,566,308,778,174.
        @return:
        """
        image_ids = []
        images_array = snapshot_description.split('ami-')[1:]
        for image in images_array:
            image_ids.append(f'ami-{image.split(" ")[0]}')
        return image_ids

    def __get_ami_ids(self):
        """
        This methos returns all image ids
        @return:
        """
        images = self.__ec2_operations.get_images()
        image_ids = []
        for image in images:
            image_ids.append(image.get('ImageId'))
        return image_ids

    def zombie_snapshots(self):
        """
        This methods removes the zombie snapshots
        @return:
        """
        snapshots = self.__ec2_operations.get_snapshots()
        zombie_snapshots = []
        image_ids = self.__get_ami_ids()
        for snapshot in snapshots:
            if snapshot.get('Description'):
                snapshot_images = self.__get_image_ids_from_description(snapshot.get('Description'))
                if set(snapshot_images) - set(image_ids):
                    zombie_snapshots.append(snapshot.get('SnapshotId'))
        for zombie_id in zombie_snapshots:
            if self.dry_run == "no":
                self.__ec2_client.delete_snapshot(SnapshotId=zombie_id)
        return zombie_snapshots

    def zombie_elastic_ip(self):
        """
        This method retuns all the unused elasticIps
        @return:
        """
        addresses = self.__ec2_operations.get_elastic_ips()
        zombie_ids = []
        for address in addresses:
            if not address.get('NetworkInterfaceId'):
                zombie_ids.append(address.get('AllocationId'))
        for zombie_id in zombie_ids:
            if self.dry_run == "no":
                self.__ec2_client.release_address(AllocationId=zombie_id)
        return zombie_ids
