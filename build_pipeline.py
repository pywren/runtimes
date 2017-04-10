
from ruffus import *
from fabric.api import execute
import fabfile_builder


# create anaconda environments for the supported python versions

CONFIG_FILES = ['default_2.7.yaml']
BUILD_WORKING = "build.working"

AWS_REGION = 'us-west-2'
UNIQUE_INSTANCE_NAME = 'pywren_builder'

def params():
    for f in CONFIG_FILES:
        infile = os.path.join("runtime_configs", f)
        outfile = os.path.join(BUILD_WORKING, f + ".success.pickle")
        yield infile, outfile


STAGING_URL_BASE = "s3://ericmjonas-public/pywren-staging/"
    
@mkdir(BUILD_WORKING)
@files(params)
def build_runtime(infile, outfile):

    hosts = fabfile_builder.get_target_instance(AWS_REGION, UNIQUE_INSTANCE_NAME)
    execute(fabfile_builder.build_runtime, config=hosts, 
            hosts=hosts)
    execute(fabfile_builder.shrink_runtime, hosts=hosts)

    s3_url = STAGING_URL_BASE + os.path.basename(infile)

    execute(fabfile_builder.deploy_runtime, 
            s3_url_base=s3_url, runtime_config_filename=infile, 
            hosts=hosts)

    ## test the runtime
    

BUCKETS = ['pywren-public-us-west-1', 
           'pywren-public-us-east-1', 
           'pywren-public-us-west-2', 
           'pywren-public-us-east-2']

@transform(create_runtimes)
def shard_runtimes(staged_runtime_sentinel, deploy_runtime_sentinel):
    for runtime:
        for bucket:
            pass


if __name__ == "__main__":
    pipeline_run([build_runtime])
            
    
