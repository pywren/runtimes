from fabric.api import env
from dockerfabric import tasks as docker
from dockerfabric.apiclient import docker_fabric
print(docker_fabric().version())
