"""
fab -f fabfile_builer.py -R builder conda_setup_mkl conda_clean package_all


"""
from fabric.api import local, env, run, put, cd, task, sudo, settings, warn_only, lcd, path, get, execute, hide
from fabric.contrib import project
import boto3
import cloudpickle
import json
import base64
import cPickle as pickle
import json
import runtimes
import yaml
import os
import copy
from shrinkruntime import * 


DEFAULT_TGT_AMI = 'ami-7172b611'
DEFAULT_REGION = 'us-west-2'
DEFAULT_UNIQUE_INSTANCE_NAME = 'pywren_builder'
DEFAULT_EC2_KEY_NAME='ec2-us-west-2'
DEFAULT_INSTANCE_TYPE='m4.large'

s3url = "s3://ericmjonas-public/condaruntime.python3.stripped.scipy-cvxpy-sklearn.mkl_avx2.tar.gz"

# this is our temporary working directory where we store build artifacts
# and downloaded code 
CONDA_BUILD_DIR = "/tmp/conda" 
# this is where we actually install the runtime
CONDA_INSTALL_DIR = "/tmp/condaruntime"


def tags_to_dict(d):
    return {a['Key'] : a['Value'] for a in d}

def get_target_instance(region_name, unique_instance_name):
    res = []
    ec2 = boto3.resource('ec2', region_name=region_name)

    for i in ec2.instances.all():
        if i.state['Name'] == 'running':
            d = tags_to_dict(i.tags)
            if d['Name'] == unique_instance_name:
                res.append('ec2-user@{}'.format(i.public_dns_name))
    print "found", res
    return {'builder' : res}

env.roledefs.update(get_target_instance(DEFAULT_REGION, 
                                        DEFAULT_UNIQUE_INSTANCE_NAME))

@task
def launch(region=DEFAULT_REGION, 
           tgt_ami = DEFAULT_TGT_AMI, 
           unique_instance_name = DEFAULT_UNIQUE_INSTANCE_NAME, 
           ec2_key_name = DEFAULT_EC2_KEY_NAME, 
           instance_type = DEFAULT_INSTANCE_TYPE):

    ec2 = boto3.resource('ec2', region_name=region)

    instances = ec2.create_instances(ImageId=tgt_ami, MinCount=1, MaxCount=1, 
                                     KeyName=ec2_key_name, 
                                     InstanceType=instance_type)
    inst = instances[0]

    inst.wait_until_running()
    inst.reload()
    inst.create_tags(
        Resources=[
            inst.instance_id
        ],
        Tags=[
            {
                'Key': 'Name',
                'Value': unique_instance_name
            },
        ]
    )


@task        
def ssh():
    if env.host_string == None:
        print "no host found"
    else:
        local("ssh -A " + env.host_string)


@task
def terminate():
    ec2 = boto3.resource('ec2', region_name=DEFAULT_REGION)

    insts = []
    for i in ec2.instances.all():
        if i.state['Name'] == 'running':
            d = tags_to_dict(i.tags)
            if d['Name'] == DEFAULT_UNIQUE_INSTANCE_NAME:
                i.terminate()
                insts.append(i)




def build_runtime_from_config(runtime_config):

    run("rm -Rf {}".format(CONDA_BUILD_DIR))
    run("rm -Rf {}".format(CONDA_INSTALL_DIR))
    run("mkdir -p {}".format(CONDA_BUILD_DIR))
    
    with cd(CONDA_BUILD_DIR):
        run("wget {} -O miniconda.sh ".format(runtime_config['miniconda_url']))
        run("bash miniconda.sh -b -p {}".format(CONDA_INSTALL_DIR))
        with path("{}/bin".format(CONDA_INSTALL_DIR), behavior="prepend"):
            run("conda install -q -y python={}".format(runtime_config['pythonver']))

            for mode in ['install', 'force']:
                if mode == 'force':
                    cmdstr = 'conda install -q -y --force'
                else:
                    cmdstr = 'conda install -q -y'
                for c in runtime_config['conda'][mode]:
                    if isinstance(c, tuple):
                        run("{} -c {} {}".format(cmdstr, c[0], c[1]))
                    else:
                        run("{} {}".format(cmdstr, c))
            for mode in ['install', 'upgrade']:
                if mode == 'upgrade':
                    cmdstr = 'pip install --upgrade'
                else:
                    cmdstr = 'pip install'
                for c in runtime_config['pip'][mode]:
                    run("{} {}".format(cmdstr, c))
            for cmd in runtime_config['extracmds']:
                run(cmd)

def format_freeze_str(x):
    packages = x.splitlines()
    return [a.split("==") for a in packages]

@task
def get_runtime_pip_freeze(conda_install_dir):
    return run("{}/bin/pip freeze 2>/dev/null".format(conda_install_dir))

@task
def get_runtime_python_ver(conda_install_dir):
    return run("{}/bin/python --version".format(conda_install_dir))

@task
def get_preinstalls(conda_install_dir):
    return run('{}/bin/python -c "import pkgutil;import json;print(json.dumps([(mod, is_pkg) for _, mod, is_pkg in pkgutil.iter_modules()]))"'.format(conda_install_dir))


@task
def get_conda_root_env(conda_install_dir):
    return run("{}/bin/conda env export -n root 2>/dev/null".format(conda_install_dir))

@task
def build_runtime(config):
    runtime_config = runtimes.load_runtime_config(config)
    build_runtime_from_config(runtime_config)

@task 
def shrink_runtime():
    execute(shrink_conda_clean, CONDA_INSTALL_DIR)
    execute(shrink_remove_pkg, CONDA_INSTALL_DIR)
    execute(shrink_remove_non_avx2_mkl, CONDA_INSTALL_DIR)
    execute(shrink_strip_shared_libs, CONDA_INSTALL_DIR)
    execute(shrink_delete_pyc, CONDA_INSTALL_DIR)
    res = execute(get_runtime_size, CONDA_INSTALL_DIR)
    print "The runtime is", res



def create_runtime_package_metadata(conda_install_dir):

    python_ver_str = execute(get_runtime_python_ver, conda_install_dir)
    python_ver = python_ver_str.values()[0] # HACK 
    python_ver = python_ver.split(" ")[1]

    freeze_str = execute(get_runtime_pip_freeze, conda_install_dir)
    freeze_str_single = freeze_str.values()[0] # HACK 

    freeze_pkgs = format_freeze_str(freeze_str_single)

    preinstalls_str = execute(get_preinstalls, conda_install_dir)
    preinstalls_str_single = preinstalls_str.values()[0]
    preinstalls = json.loads(preinstalls_str_single)
    conda_env_yaml = execute(get_conda_root_env, conda_install_dir)
    conda_env_yaml_single = conda_env_yaml.values()[0]  # HACK

    conda_env = yaml.load(conda_env_yaml_single)
    runtime_dict = {'python_ver' : python_ver, 
                    'pkg_ver_list' : freeze_pkgs,
                    'preinstalls' : preinstalls, 
                    'conda_env_config': conda_env}
    return runtime_dict


def tar_runtime(conda_install_dir, conda_build_dir):
    # FIXME this isn't totally install-dir agnostic
    out_tarball_path = os.path.abspath(os.path.join(conda_build_dir, 'condaruntime.tar.gz'))
    with cd(conda_install_dir + "/../"):
        run("tar czf {} condaruntime".format(out_tarball_path))
    return out_tarball_path


def put_runtime_url(tar_path, s3url):
    get(tar_path, local_path="/tmp/condaruntime.tar.gz")
    local("aws s3 cp /tmp/condaruntime.tar.gz {}".format(s3url))


def deploy_runtime_urls(runtime_tar_s3_url, runtime_meta_s3_url, 
                        runtime_config):
    # get the metadata 
    runtime_dict = create_runtime_package_metadata(CONDA_INSTALL_DIR)
    runtime_dict['runtime_config'] = runtime_config
    
    # tar the runtime
    tar_path = tar_runtime(CONDA_INSTALL_DIR, CONDA_BUILD_DIR)

    put_runtime_url(tar_path, runtime_tar_s3_url)

    # Write the metadata and stick on S3
    runtime_dict['urls'] = [runtime_tar_s3_url]
    with open('runtime.meta.json', 'w') as outfile:
        json.dump(runtime_dict, outfile)        
        outfile.flush()

    local("aws s3 cp runtime.meta.json {}".format(runtime_meta_s3_url))


@task 
def deploy_runtime(s3_url_base, runtime_config_filename):

    runtime_config = runtimes.load_runtime_config(config)

    runtime_tar_s3_url = s3_url_base + ".tar.gz"
    runtime_meta_s3_url = s3_url_base + ".meta.json"

    deploy_runtime_urls(runtime_tar_s3_url, runtime_meta_s3_url, 
                        runtime_config)

@task
def shard_runtime(s3_url_base_source, s3_url_base_dest, 
                  num_shards):
    runtime_tar_s3_url = s3_url_base_source + ".tar.gz"
    runtime_meta_s3_url = s3_url_base_source + ".meta.json"
    
    local("aws s3 cp {} runtime.meta.json".format(runtime_meta_s3_url))
    meta_dict = json.load(open('runtime.meta.json', 'r'))
    assert meta_dict['urls'][0] == runtime_tar_s3_url
    
    # generate the URLs
    
    shard_urls = []
    for shard_id in xrange(int(num_shards)):
        bucket_name, key = runtimes.split_s3_url(runtime_tar_s3_url)
        shard_key = runtimes.get_s3_shard(key, shard_id)
        hash_s3_key = runtimes.hash_s3_key(shard_key)
        shard_url = "s3://{}/{}".format(bucket_name, hash_s3_key)
        local("aws s3 cp {} {}".format(runtime_tar_s3_url, 
                                       shard_url))
        shard_urls.append(shard_url)
    print shard_urls
    meta_dict['urls'] = shard_urls
    with open('runtime.meta.json', 'w') as outfile:
        json.dump(meta_dict, outfile)        
        outfile.flush()

    local("aws s3 cp runtime.meta.json {}".format(s3_url_base_dest + ".meta.json"))


