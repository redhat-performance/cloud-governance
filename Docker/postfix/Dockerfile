# https://xc2.wb1.xyz/post/how-to-run-a-postfix-mail-server-in-a-docker-container/
FROM alpine:3.13

# Install dependencies
RUN apk add --no-cache --update postfix cyrus-sasl ca-certificates bash && \
    apk add --no-cache --upgrade musl musl-utils && \
    # Clean up
    (rm "/tmp/"* 2>/dev/null || true) && (rm -rf /var/cache/apk/* 2>/dev/null || true)

# Mark used folders
VOLUME [ "/var/spool/postfix", "/etc/postfix" ]

# Expose mail submission agent port
EXPOSE 587

# Configure Postfix on startup
COPY docker-entrypoint.sh /usr/local/bin/

RUN chown postfix:postfix /etc/postfix /etc/postfix/main.cf && \
    chmod 777 /usr/local/bin/docker-entrypoint.sh &&

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Start postfix in foreground mode
CMD ["postfix", "start-fg"]
