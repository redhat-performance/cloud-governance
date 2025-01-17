#!/bin/bash
set -e

# usage: file_env VAR [DEFAULT]
#    ie: file_env 'XYZ_PASSWORD' 'example'
# (will allow for "$XYZ_PASSWORD_FILE" to fill in the value of
#  "$XYZ_PASSWORD" from a file, especially for Docker's secrets feature)
# copied from mariadb docker entrypoint file
file_env() {
	local var="$1"
	local fileVar="${var}_FILE"
	local def="${2:-}"
	if [ "${!var:-}" ] && [ "${!fileVar:-}" ]; then
		echo >&2 "error: both $var and $fileVar are set (but are exclusive)"
		exit 1
	fi
	local val="$def"
	if [ "${!var:-}" ]; then
		val="${!var}"
	elif [ "${!fileVar:-}" ]; then
		val="$(< "${!fileVar}")"
	fi
	export "$var"="$val"
	unset "$fileVar"
}

#file_env 'POSTFIX_RELAY_PASSWORD'

#if [ -z "$POSTFIX_HOSTNAME" -a -z "$POSTFIX_RELAY_HOST" ]; then
#    echo >&2 'error: relay options are not specified '
#    echo >&2 '  You need to specify POSTFIX_HOSTNAME, POSTFIX_RELAY_HOST)'
#    exit 1
#fi

# Create postfix folders
mkdir -p /var/spool/postfix/
mkdir -p /var/spool/postfix/pid

# Disable SMTPUTF8, because libraries (ICU) are missing in Alpine
postconf -e "smtputf8_enable=no"

# Log to stdout
postconf -e "maillog_file=/dev/stdout"

# Update aliases database. It's not used, but postfix complains if the .db file is missing
postalias /etc/postfix/aliases

# Disable local mail delivery
postconf -e "mydestination="

# Limit message size to 10MB
postconf -e "message_size_limit=10240000"

# Reject invalid HELOs
postconf -e "smtpd_delay_reject=yes"
postconf -e "smtpd_helo_required=yes"
postconf -e "smtpd_helo_restrictions=permit_mynetworks,reject_invalid_helo_hostname,permit"

# Don't allow requests from outside
postconf -e "mynetworks=127.0.0.0/8,${POSTFIX_ALLOWED_IPS}"

# Set up hostname
#postconf -e myhostname=$POSTFIX_HOSTNAME

# Do not relay mail from untrusted networks
postconf -e relay_domains=$POSTFIX_RELAY_DOMAINS

# Relay configuration
postconf -e relayhost=$POSTFIX_RELAY_HOST
#echo "$POSTFIX_RELAY_HOST $POSTFIX_RELAY_USER:$POSTFIX_RELAY_PASSWORD" >> /etc/postfix/sasl_passwd
#postmap lmdb:/etc/postfix/sasl_passwd
#postconf -e "smtp_sasl_auth_enable=yes"
#postconf -e "smtp_sasl_password_maps=lmdb:/etc/postfix/sasl_passwd"
#postconf -e "smtp_sasl_security_options=noanonymous"
#postconf -e "smtpd_recipient_restrictions=reject_non_fqdn_recipient,reject_unknown_recipient_domain,reject_unverified_recipient"

# Use 587 (submission)
sed -i -r -e 's/^#submission/submission/' /etc/postfix/master.cf

echo
echo 'postfix configured. Ready for start up.'
echo

exec "$@"
