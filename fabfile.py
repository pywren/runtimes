

from fabric.api import local, env, run, put, cd, task, sudo, get, settings, warn_only, lcd
from fabric.contrib import project
import boto3
import cloudpickle
import json
import base64
from six.moves import cPickle as pickle
import time
import subprocess
from sys import platform


"""
conda notes

be sure to call conda clean --all before compressing



"""

env.roledefs['m'] = ['jonas@c65']
if platform == 'linux':
   try:
      r = subprocess.check_output("docker port test_sshd 22", shell=True)
   except:
      pass

@task
def deploy():
        local('git ls-tree --full-tree --name-only -r HEAD > .git-files-list')
    
        project.rsync_project("/data/jonas/pywren-runtimes/", local_dir="./",
                              exclude=['*.npy', "*.ipynb", 'data', "*.mp4", 
                                       "*.pdf", "*.png"],
                              extra_opts='--files-from=.git-files-list')


container_name = "test_sshd"

@task
def del_container():
    run("docker stop test_sshd")
    run("docker rm test_sshd")

@task
def launch_container():
    run("docker run -dti -p :22 --name {container_name} amazonlinux:2016.09 bash"\
        .format(container_name=container_name))
    run("docker exec {container_name} yum install -y openssh-server nmap shadow-utils util-linux wget bzip2".format(container_name=container_name))
    run("docker exec {container_name} /etc/init.d/sshd start".format(container_name=container_name))
    run("docker exec {container_name} useradd ec2-user".format(container_name=container_name))
    run("docker exec {container_name} mkdir /home/ec2-user/.ssh/".format(container_name=container_name))
    run("docker exec {container_name} chown ec2-user /home/ec2-user/.ssh".format(container_name=container_name))
    run("docker cp ~/.ssh/id_rsa.pub {container_name}:/home/ec2-user/.ssh/authorized_keys".format(container_name=container_name))
    run("docker exec {container_name} chown ec2-user /home/ec2-user/.ssh/authorized_keys".format(container_name=container_name))
    
@task
def launch_checkpointed_container():
   run("docker run -dti -p :22 --name test_sshd test_sshd_jonas_post_default_3.6")
   run("docker exec test_sshd /etc/init.d/sshd start")

