import json
import time
import docker

docker_client = docker.from_env(version="auto")

c = docker_client.containers.list()[0]
s = c.stats(decode=True, stream=False)
print(s)
for m in s:
    print(json.dumps(m, indent=2))

