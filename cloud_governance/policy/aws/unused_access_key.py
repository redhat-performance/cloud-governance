from cloud_governance.common.utils.configs import (
    UNUSED_ACCESS_KEY_DAYS,
    UNUSED_ACCESS_KEY_REMINDER_DAYS,
    DELETE_ACCESS_KEY_DAYS,
)
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.common.logger.init_logger import logger


class UnusedAccessKey(AWSPolicyOperations):
    RESOURCE_ACTION = "DeActivate"

    def __init__(self):
        super().__init__()
        self._mail_message = MailMessage()
        self._postfix_mail = Postfix()

    def _send_reminder_and_update_tag(self, user_name: str, tags: list, access_key_label: str,
                                     age_days: int, reminder_count: int):
        """Send one reminder email and set IAM user tag UnusedAccessKeyNReminderCount to reminder_count."""
        tag_key = f"UnusedAccessKey{access_key_label.split()[-1]}ReminderCount"
        to_user = self.get_tag_name_from_tags(tags=tags, tag_name='User') or user_name
        display_name = self._mail_message.get_user_ldap_details(user_name=to_user) or to_user
        subject, body = self._mail_message.unused_access_key_reminder(
            name=display_name,
            user=user_name,
            account=self.account or self._environment_variables_dict.get('account', ''),
            age_days=age_days,
            key_label=access_key_label,
            reminder_number=reminder_count,
            deactivate_days=UNUSED_ACCESS_KEY_DAYS,
        )
        try:
            self._postfix_mail.send_email_postfix(to=to_user, cc=[], subject=subject, content=body)
            self._iam_operations.tag_user(user_name, [{'Key': tag_key, 'Value': str(reminder_count)}])
            logger.info(f"Sent access key rotation reminder {reminder_count}/2 to {to_user} for {user_name}")
        except Exception as err:
            logger.warning(f"Failed to send reminder or update tag for {user_name}: {err}")

    def run_policy_operations(self):
        """
        For key age > 80 and <= 90 days: send up to two reminder emails to rotate the key.
        For key age > 90 days: deactivate the access key after grace period.
        For keys we previously deactivated (tagged with UnusedAccessKeyNInactiveDate): if key age
        > DELETE_ACCESS_KEY_DAYS (120), delete the key (~30 days after deactivation). Only keys we tagged are deleted.
        """
        unused_access_keys = []
        iam_users_access_keys = self._get_iam_users_access_keys()
        for username, user_data in iam_users_access_keys.items():
            tags = user_data.get('tags', user_data.get('Tags', []))
            region = user_data['region']
            user_name = username

            for access_key_label, access_key_data in user_data.items():
                if 'access key' not in access_key_label.lower():
                    continue
                last_activity_days = access_key_data.get('last_activity_days')
                age_days = access_key_data.get('age_days')
                status = (access_key_data.get('status') or '').lower()
                if age_days is None:
                    continue
                age_days = int(age_days)

                # Inactive key: delete if (we tagged it and key age > 120 days) OR (DELETE_INACTIVE_KEYS_WITHOUT_TAG and key age > 120)
                if status == 'inactive':
                    key_num = access_key_label.split()[-1]
                    inactive_tag_key = f"UnusedAccessKey{key_num}InactiveDate"
                    inactive_date_str = self.get_tag_name_from_tags(tags=tags, tag_name=inactive_tag_key)
                    delete_all_inactive = self._environment_variables_dict.get('DELETE_INACTIVE_KEYS_WITHOUT_TAG', False)
                    should_delete = age_days > DELETE_ACCESS_KEY_DAYS and (inactive_date_str or delete_all_inactive)
                    if should_delete:
                        if self._dry_run == 'no':
                            try:
                                self._delete_inactive_access_key(user_name, access_key_label)
                                cleanup_result = True
                            except Exception as err:
                                logger.warning(f"Failed to delete inactive key for {user_name}: {err}")
                                cleanup_result = False
                        else:
                            cleanup_result = False
                        resource_data = self._get_es_schema(
                            resource_id=user_name,
                            user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                            skip_policy=self.get_skip_policy_value(tags=tags),
                            cleanup_days=DELETE_ACCESS_KEY_DAYS,
                            dry_run=self._dry_run,
                            name=user_name,
                            region=region,
                            cleanup_result=str(cleanup_result) if self._dry_run == 'no' else 'dry_run',
                            resource_action='Delete',
                            cloud_name=self._cloud_name,
                            resource_type='UnusedAccessKey',
                            resource_state='Inactive',
                            age_days=age_days,
                            last_activity_days=last_activity_days,
                            unit_price=0,
                        )
                        unused_access_keys.append(resource_data)
                    continue

                if not self._has_active_access_keys(user_name, access_key_label):
                    continue
                if self.get_skip_policy_value(tags=tags) in ('NOTDELETE', 'SKIP'):
                    continue

                cleanup_result = False
                cleanup_days = 0

                # Reminder window: 80 < age <= 90 – send up to two reminders
                if UNUSED_ACCESS_KEY_REMINDER_DAYS < age_days <= UNUSED_ACCESS_KEY_DAYS:
                    tag_key = f"UnusedAccessKey{access_key_label.split()[-1]}ReminderCount"
                    reminder_val = self.get_tag_name_from_tags(tags=tags, tag_name=tag_key)
                    reminder_count = 0
                    if reminder_val in ('1', '2'):
                        reminder_count = int(reminder_val)
                    if reminder_count < 2 and self._dry_run == 'no':
                        self._send_reminder_and_update_tag(
                            user_name=user_name,
                            tags=tags,
                            access_key_label=access_key_label,
                            age_days=age_days,
                            reminder_count=reminder_count + 1,
                        )
                    continue

                # Deactivate when age > 90 days
                if age_days >= UNUSED_ACCESS_KEY_DAYS:
                    cleanup_days = self.get_clean_up_days_count(tags=tags)
                    cleanup_result = self.verify_and_delete_resource(
                        resource_id=user_name,
                        tags=tags,
                        clean_up_days=cleanup_days,
                        access_key_label=access_key_label,
                    )
                    resource_data = self._get_es_schema(
                        resource_id=user_name,
                        user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                        skip_policy=self.get_skip_policy_value(tags=tags),
                        cleanup_days=cleanup_days,
                        dry_run=self._dry_run,
                        name=user_name,
                        region=region,
                        cleanup_result=str(cleanup_result),
                        resource_action=self.RESOURCE_ACTION,
                        cloud_name=self._cloud_name,
                        resource_type='UnusedAccessKey',
                        resource_state='Active',
                        age_days=age_days,
                        last_activity_days=last_activity_days,
                        unit_price=0,
                    )
                    unused_access_keys.append(resource_data)
                    if not cleanup_result:
                        self.update_resource_day_count_tag(
                            resource_id=user_name, cleanup_days=cleanup_days, tags=tags
                        )

        return unused_access_keys
