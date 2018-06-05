"""
fab -f fabfile_builer.py -R builder conda_setup_mkl conda_clean package_all


"""
from __future__ import print_function
from fabric.api import local, env, run, put, cd, task, sudo, settings, warn_only, lcd, path, get, execute, hide
from fabric.contrib import project
import boto3
import cloudpickle
import json
import base64
import pickle
import json
import runtimes
import yaml
import os
import sys
import copy
import subprocess
from shrinkruntime import * 
from multiprocessing.pool import ThreadPool


env.disable_known_hosts =True

DEFAULT_BUILDER = {'aws_region' : None, 
                   'tgt_ami' : 'ami-7172b611', 
                   'gpu_tgt_ami' : 'ami-dfb13ebf', 
                   'instance_name' : 'pywren_builder', 
                   'aws_ec2_key' : None, 
                   'instance_type' : 'm4.large'}

BUILDER_ENV = DEFAULT_BUILDER.copy()

BUILDER_ENV.update(yaml.load(open("builder_config.yaml", 'r')))


# this is our temporary working directory where we store build artifacts
# and downloaded code 
CONDA_BUILD_DIR = "/tmp/conda" 
# this is where we actually install the runtime
CONDA_INSTALL_DIR = "/tmp/condaruntime"

if sys.platform == 'linux':
   r = subprocess.check_output("docker port test_sshd 22", shell=True)
   env.roledefs['d'] = ['ec2-user@{}'.format(r.decode('ascii').strip())]


def tags_to_dict(d):
    if d is None or len(d) == 0:
        return {}
    return {a['Key'] : a['Value'] for a in d}

def get_target_instance(region_name, unique_instance_name, 
                        rolename='builder'):
    res = []
    ec2 = boto3.resource('ec2', region_name=region_name)

    for i in ec2.instances.all():
        if i.state['Name'] == 'running':
            d = tags_to_dict(i.tags)
            if d is not None and d.get('Name', "") == unique_instance_name:
                res.append('ec2-user@{}'.format(i.public_dns_name))

    return {rolename : res}

env.roledefs.update(get_target_instance(BUILDER_ENV['aws_region'], 
                                        BUILDER_ENV['instance_name']))


@task
def launch(region = BUILDER_ENV['aws_region'],
           tgt_ami = BUILDER_ENV['tgt_ami'], 
           unique_instance_name = BUILDER_ENV['instance_name'], 
           ec2_key_name = BUILDER_ENV['aws_ec2_key'], 
           instance_type = BUILDER_ENV['instance_type']):

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
def setup_ami():
    sudo('yum -y -q groupinstall "Development Tools" ')
    sudo('yum -y -q install cmake ')

@task        
def ssh():
    if env.host_string == None:
        print("no host found")
    else:
        local("ssh -A " + env.host_string)


@task
def terminate(region = BUILDER_ENV['aws_region'], 
              unique_instance_name = BUILDER_ENV['instance_name']):
    ec2 = boto3.resource('ec2', region_name=region)

    insts = []
    for i in ec2.instances.all():
        if i.state['Name'] == 'running':
            d = tags_to_dict(i.tags)
            if d['Name'] == unique_instance_name:
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
                    if isinstance(c, tuple) or isinstance(c, list):
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
    #execute(shrink_remove_non_avx2_mkl, CONDA_INSTALL_DIR)
    execute(shrink_strip_shared_libs, CONDA_INSTALL_DIR)
    execute(shrink_delete_pyc, CONDA_INSTALL_DIR)
    execute(shrink_delete_static_libs, CONDA_INSTALL_DIR)
    res = execute(get_runtime_size, CONDA_INSTALL_DIR)
    for k, v in res.items():
        print("The runtime is", int(v)/1e3, "MB")


def get_first(x):
    for k, v in x.items():
        return v

def create_runtime_package_metadata(conda_install_dir):

    python_ver_str = execute(get_runtime_python_ver, conda_install_dir)
    python_ver = get_first(python_ver_str) # HACK 
    python_ver = python_ver.split(" ")[1]
    python_ver = ".".join(python_ver.split(".")[:2])

    freeze_str = execute(get_runtime_pip_freeze, conda_install_dir)
    freeze_str_single = get_first(freeze_str) # HACK 

    freeze_pkgs = format_freeze_str(freeze_str_single)

    preinstalls_str = execute(get_preinstalls, conda_install_dir)
    preinstalls_str_single = get_first(preinstalls_str)
    preinstalls = json.loads(preinstalls_str_single)
    conda_env_yaml = execute(get_conda_root_env, conda_install_dir)
    conda_env_yaml_single = get_first(conda_env_yaml)  # HACK

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
        run("tar czfS {} condaruntime".format(out_tarball_path))
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

    runtime_config = runtimes.load_runtime_config(runtime_config_filename)

    runtime_tar_s3_url = s3_url_base + ".tar.gz"
    runtime_meta_s3_url = s3_url_base + ".meta.json"

    deploy_runtime_urls(runtime_tar_s3_url, runtime_meta_s3_url, 
                        runtime_config)
    return runtime_tar_s3_url, runtime_meta_s3_url

@task
def shard_runtime(s3_url_base_source, s3_url_base_dest, 
                  num_shards):
    runtime_tar_s3_url = s3_url_base_source + ".tar.gz"
    runtime_meta_s3_url = s3_url_base_source + ".meta.json"
    
    local("aws s3 cp {} runtime.meta.json".format(runtime_meta_s3_url))
    meta_dict = json.load(open('runtime.meta.json', 'r'))
    assert meta_dict['urls'][0] == runtime_tar_s3_url
    
    # generate the URLs
    source_bucket_name, source_key_name = runtimes.split_s3_url(runtime_tar_s3_url)
    dest_bucket_name, dest_key_name  = runtimes.split_s3_url(s3_url_base_dest)
    dest_key_tar_gz = dest_key_name + ".tar.gz"

    s3 = boto3.resource('s3')
    
    dest_loc_info = s3.meta.client.get_bucket_location(Bucket=dest_bucket_name)
    dest_region = dest_loc_info['LocationConstraint']
    if dest_region is None:
        dest_region = 'us-west-1'


    def copy_s3(source_bucket, source_key, 
             dest_bucket, dest_key):
        print("copying", "s3://{}/{}".format(source_bucket, source_key), "to", "s3://{}/{}".format(dest_bucket, dest_key))

        copy_source = {
            'Bucket': source_bucket,
            'Key': source_key, 
        }
        s3.meta.client.copy(copy_source, dest_bucket, dest_key)
        
    pool = ThreadPool(16)

    shard_urls = []
    for shard_id in range(int(num_shards)):

        shard_key = runtimes.get_s3_shard(dest_key_tar_gz, shard_id)
        hash_s3_key = runtimes.hash_s3_key(shard_key)
        shard_url = "s3://{}/{}".format(dest_bucket_name, hash_s3_key)
        
        pool.apply_async(copy_s3, args=(source_bucket_name, source_key_name, 
                                        dest_bucket_name, hash_s3_key))

        shard_urls.append(shard_url)

    pool.close()
    pool.join()
    meta_dict['urls'] = shard_urls
    with open('runtime.meta.json', 'w') as outfile:
        json.dump(meta_dict, outfile)        
        outfile.flush()

    local("aws s3 cp runtime.meta.json --region={} {}".format(dest_region, 
                                                              s3_url_base_dest + ".meta.json"))


@task
def backup_and_strip_sos(conda_build_dir, BACKUP_PATH = "/tmp/condaruntime.backup"):
    # get all of the SOs that are big OR match some glob



    # first create a backup, preserving the path
    run("mkdir -p {}".format(BACKUP_PATH))
    with cd(conda_build_dir):
        for tgt_glob in ["*mkl*.so", "*Qt*.so.*", "*llvmlite.so"]:

            run('find . -name "{}" -size +1M -exec cp --parents \{{\}} {} \;'.format(tgt_glob, BACKUP_PATH))

            # use objcopy to copy them minus certain sections, and
            for section in ['.text']: # don't know if these ones work -->  '.rodata', '.bss']:
                run('find . -name "{}" -size +1M -exec objcopy --remove-section={} \{{\}}  \{{\}}  \;'.format(tgt_glob, section))



    
@task 
def get_metadata(conda_install_dir, outfile="package.meta.json"):
    d = create_runtime_package_metadata(conda_install_dir)
    json.dump(d, open(outfile, 'w'), sort_keys=True, indent=4)
    
@task
def file_remap_dir(CONDA_BUILD_DIR, conda_backup_dir, out_path):
    mapping = {}
    with cd(CONDA_BUILD_DIR):
        a = run("find {} -type f".format(conda_backup_dir))
        for path in a.splitlines():
            k = os.path.relpath(path, conda_backup_dir)
            mapping[k] = path
    json.dump(mapping, open(out_path, 'w'), sort_keys=True, indent=4)


def assemble_runtime(config_filename, meta_filename, 
                     tar_filename, remapping_filename):
    """
    Create the meta.json but with paths to files instead of s3 urls
    """

    # load the runtime metadata
    runtime_dict = json.load(open(meta_filename, 'r'))

    # load the config data 
    runtime_dict['runtime_config'] = yaml.load(config_filename)
    
    runtime_dict['urls'] = tar_filename    
    runtime_dict['lib_mapping'] = json.load(open(remapping_filename, 'r'))

    return runtime_dict

@task
def upload_runtime(runtime_filename, s3_url_base):
    pass


@task
def test_tar_runtime():
    
    res = tar_runtime(CONDA_INSTALL_DIR, CONDA_BUILD_DIR)
    print("res=", res)

@task
def test_deploy():


    bucket_name = 'jonas-us-west-2'
    runtime_s3_basekey = "runtimes/test8"

    def tarfile_create_s3urls(bucket_name, runtime_s3_basekey):
        return ["s3://{}/{}/runtime.tar.gz".format(bucket_name, runtime_s3_basekey)]

    def mapping_create_s3urls(mapped_files, bucket_name, 
                              runtime_s3_basekey):
        out_map = {}
        for k, vi in mapped_files.items():
            out_map[k] = ["s3://{}/{}/mapped_files/{}".format(bucket_name, runtime_s3_basekey, k)]
        return out_map
    
    def s3_puts(local_file, s3_urls):
        for url in s3_urls:
            local('aws s3 cp {} {}'.format(local_file, url))

    config_filename = 'runtime_configs/default_3.6.yaml'
    meta_filename = 'packages.json'
    tar_filename = '/tmp/conda/condaruntime.tar.gz'
    mapping_filename = 'mapping.json'

    runtime_meta = assemble_runtime(config_filename, 
                                        meta_filename, 
                                        tar_filename, mapping_filename)
    

    ### Main Tarfile 
    tar_filename = runtime_meta['urls'] 

    tar_filename_local = get(tar_filename)[0]

    tar_filename_s3_urls = tarfile_create_s3urls(bucket_name, 
                                                 runtime_s3_basekey)
    s3_puts(tar_filename_local, tar_filename_s3_urls)

    runtime_meta['urls'] = tar_filename_s3_urls


    ### mapped libraries
    mapped_files = runtime_meta['lib_mapping']
    mapped_s3_urls = mapping_create_s3urls(mapped_files, bucket_name, 
                                         runtime_s3_basekey)

    for path, remote_filename in mapped_files.items():
        filename_local = get(remote_filename)[0]
        s3_urls = mapped_s3_urls[path]
        s3_puts(filename_local, s3_urls)
    runtime_meta['lib_mapping'] = mapped_s3_urls
    
    # put the final file
    json.dump(runtime_meta, open("meta.json", 'w'))
    s3_puts("meta.json", ["s3://{}/{}/meta.json".format(bucket_name,runtime_s3_basekey)])

