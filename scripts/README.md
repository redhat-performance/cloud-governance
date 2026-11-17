# IAM hygiene scripts

Three standalone scripts that use only `boto3` and import nothing from
`cloud_governance`. They report by default; a change requires the action flag
**and** `--apply`.

In this repo use `.venv/bin/python` instead of `python`.

## delete_access_keys.py

Reports access keys older than N days (default 3).

```bash
python scripts/delete_access_keys.py            # report
python scripts/delete_access_keys.py --days 30
python scripts/delete_access_keys.py --deactivate --apply   # reversible
python scripts/delete_access_keys.py --delete --apply       # permanent
```

Options: `--days`, `--sort`, `--json`, `--show-key-ids`, `--output-file`,
`--profile`, `--region`, `--exit-zero`.

Guards: the caller's own key is never touched; a user's last Active key needs
`--force`; `--delete` only selects Inactive keys unless `--include-active`.
Exclude keys with `EXCLUDE_ACCESS_KEY_IDS=id1,id2`.

## delete_console_access.py

Removes IAM users' console password (login profile). Access keys and MFA devices
are untouched.

```bash
python scripts/delete_console_access.py          # report
python scripts/delete_console_access.py --remove
python scripts/delete_console_access.py --remove --apply
```

Options: `--include-caller`, `--exclude-user`, `--json`, `--output-file`,
`--profile`, `--region`, `--exit-zero`.

The caller's own user is skipped unless `--include-caller` is given. Root and IAM
Identity Center (SSO) users are not affected.

## delete_iam_users.py

Deletes a user when it was created more than N days ago (default 30) and its last
access is never or more than N days ago. Last access is the latest of the console
sign-in and every access key's last use.

```bash
python scripts/delete_iam_users.py               # report
python scripts/delete_iam_users.py --delete      # preview
python scripts/delete_iam_users.py --delete --apply
```

Options: `--days`, `--force`, `--exclude-user`, `--json`, `--output-file`,
`--profile`, `--region`, `--exit-zero`.

Guards: the caller's own user is never deleted; users with an MFA device are
skipped (removing MFA needs an OTP); users with a credential created within
`--days` are skipped unless `--force`.

Deleting a user is irreversible: the script removes its access keys, login
profile, certificates, SSH keys, service-specific credentials, policies, group
memberships and permissions boundary first.

## Exit status

| Code | Meaning |
| --- | --- |
| `0` | Success; nothing found, or no failures. |
| `1` | Results found, scan incomplete, or at least one change failed. |
| `2` | Invalid arguments, no credentials, or the report file could not be written. |
