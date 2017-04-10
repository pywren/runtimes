import os
from ruffus import *
from fabric.api import execute
import fabfile_builder
import subprocess
import cPickle as pickle
import runtimes

# create anaconda environments for the supported python versions

CONFIG_FILES = ['default_2.7.yaml']
BUILD_WORKING = "build.working"

AWS_REGION = 'us-west-2'
UNIQUE_INSTANCE_NAME = 'pywren_builder'

def params():
    for f in CONFIG_FILES:
        infile = os.path.join("runtime_configs", f)
        outfile = os.path.join(BUILD_WORKING, f + ".built.pickle")
        yield infile, outfile


STAGING_URL_BASE = "s3://ericmjonas-public/pywren-staging/"
    
@mkdir(BUILD_WORKING)
@files(params)
@jobs_limit(1)
def build_runtime(infile, outfile):

    hosts = fabfile_builder.get_target_instance(AWS_REGION, UNIQUE_INSTANCE_NAME).values()[0]

    runtime_name = os.path.splitext(os.path.basename(infile))[0]

    execute(fabfile_builder.build_runtime, config=infile, 
            hosts=hosts)
    execute(fabfile_builder.shrink_runtime, hosts=hosts)


    s3_url = STAGING_URL_BASE + os.path.splitext(os.path.basename(infile))[0]


    deploy_results = execute(fabfile_builder.deploy_runtime, 
            s3_url_base=s3_url, runtime_config_filename=infile, 
            hosts=hosts)

    runtime_tar_s3_url, runtime_meta_s3_url = deploy_results.values()[0]


    pickle.dump({'infile' : infile, 
                 'runtime_name' : runtime_name, 
                 'runtime_tar_s3_url' : runtime_tar_s3_url, 
                 'runtime_meta_s3_url' : runtime_meta_s3_url}, 
                open(outfile, 'w'))


# create the local environments to check
CONDA_TEST_ENVS = {'2.7' : 'build-test-2.7', 
                   '3.4' : 'build-test-3.4',
                   '3.5' : 'build-test-3.5',
                   '3.6' : 'build-test-3.6'
}
                   

def conda_env_params():
    for python_ver, conda_env_name in CONDA_TEST_ENVS.items():
        yield None, conda_env_name + ".env", python_ver, conda_env_name
@jobs_limit(1)
@files(conda_env_params)
def create_environment(infile, outfile, python_ver, conda_env_name):
    print "removing old environment", conda_env_name
    subprocess.call("conda remove --name {} --all --y".format(conda_env_name), 
                    shell=True)
    print "creating new environment", conda_env_name

    subprocess.call("conda create --name={} python={} --y".format(conda_env_name,
                                                                      python_ver), 
                            shell=True)
    print "getting path", conda_env_name

    env_path = subprocess.check_output("source activate {}; printenv PATH".format(conda_env_name), 
                                shell=True)
    print "saving results"
    pickle.dump({'python_ver' : python_ver, 
                 'conda_env_name' : conda_env_name, 
                 'env_path' : env_path}, 
                open(outfile, 'w'))
    
@follows(create_environment)    
@transform(build_runtime, suffix(".built.pickle"), ".success.pickle")
def check_runtime(build_file, outfile):



    build_result = pickle.load(open(build_file, 'r'))
    tar_s3_url = build_result['runtime_tar_s3_url']
    runtime_name = build_result['runtime_name']
    build_config_file = build_result['infile']

    runtime_config_dict = runtimes.load_runtime_config(build_config_file)

    pythonver = runtime_config_dict['pythonver']
    bucket_name, key_name = runtimes.split_s3_url(tar_s3_url)

    print pythonver, type(pythonver), CONDA_TEST_ENVS

    test_env_name = CONDA_TEST_ENVS[pythonver]
    conda_env_config = pickle.load(open(test_env_name + ".env", 'r'))
    env_path = conda_env_config['env_path']
    env = os.environ.copy()
    env['PATH'] = env_path
    
    PYWREN_INSTALL_CMD = 'pip install pywren --upgrade'
    subprocess.check_output(PYWREN_INSTALL_CMD, 
                            shell=True, env=env)

    LAMBDA_INSTALL_CMD = 'pywren deploy_lambda'
    subprocess.check_output(LAMBDA_INSTALL_CMD, 
                            shell=True, env=env)

    print subprocess.check_output("python --version", 
                            shell=True, env=env)

    TEST_CMD = "python pywren_validate_runtime.py {} {}".format(bucket_name, key_name)
    res = subprocess.check_output(TEST_CMD, shell=True, env=env)
    
    pickle.dump({'res' : res, 
                 'build_file' : build_file, 
                 'runtime_name' : runtime_name, 
                 'build_config_file' : build_config_file, 
                 'tar_s3_url' : tar_s3_url}, 
                open(outfile, 'w'))

BUCKETS = ['pywren-public-us-west-1', 
           'pywren-public-us-east-1', 
           'pywren-public-us-west-2', 
           'pywren-public-us-east-2']

NUM_SHARDS = 50

@transform(check_runtime, suffix(".success.pickle"), ".deploy.pickle")
def shard_runtime(infile, outfile):
    
    validated_runtime = pickle.load(open(infile, 'r'))
    tar_s3_url = validated_runtime['tar_s3_url']
    s3_url_base_source = tar_s3_url.replace(".tar.gz", "")
    build_file = validated_runtime['build_config_file']
    runtime_name = validated_runtime['runtime_name']

    for bucket in BUCKETS:
        OUT_URL = "s3://{}/pywren.runtimes/{}".format(bucket, runtime_name)
        print OUT_URL
        execute(fabfile_builder.shard_runtime, s3_url_base_source, OUT_URL, 
                NUM_SHARDS)


if __name__ == "__main__":
    pipeline_run([build_runtime, 
                  create_environment, check_runtime, 
                  shard_runtime])
            
    
