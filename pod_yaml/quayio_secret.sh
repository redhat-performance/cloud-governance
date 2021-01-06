podman login --authfile=quayioconfig.json quay.io
oc create secret generic quayiosecret --from-file=.dockerconfigjson=quayioconfig.json --type=kubernetes.io/dockerconfigjson
oc secrets link default quayiosecret --for=pull
oc secrets link builder quayiosecret