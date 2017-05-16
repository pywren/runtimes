import os
import hashlib
import yaml
import copy

CONDA_DEFAULT_LIST = ["tblib", 
                      "numpy", 
                      "pytest", 
                      "Click", 
                      "numba", 
                      "boto3", 
                      "PyYAML", 
                      'six',
                      "cython", 'future']

PIP_DEFAULT_LIST = ['glob2', 'boto', 'certifi']
PIP_DEFAULT_UPGRADE_LIST = ['cloudpickle', 'enum34']

CONDA_ML_SET = ['scipy', 'pillow', 'cvxopt', 'scikit-learn']
PIP_ML_SET = ['cvxpy', 'redis']

CONDA_OPT_SET = ['scipy', 'cvxopt', ('mosek', 'mosek')]
PIP_OPT_SET = ['cvxpy' ]

RUNTIMES = {'minimal' : {'pythonvers' : ["2.7", "3.5", "3.6"],  
                         'packages' : { 
                             'conda_install' : CONDA_DEFAULT_LIST, 
                             'pip_install' : PIP_DEFAULT_LIST, 
                             'pip_upgrade' : PIP_DEFAULT_UPGRADE_LIST}},
            'ml' : {'pythonvers' :  ["2.7", "3.5", "3.6"],
                    'packages' : {
                        'conda_install' : CONDA_DEFAULT_LIST + CONDA_ML_SET, 
                        'pip_install' : PIP_DEFAULT_LIST + PIP_ML_SET, 
                        'pip_upgrade' : PIP_DEFAULT_UPGRADE_LIST }},
            'default' : {'pythonvers' : ["2.7", "3.5", "3.6"], 
                         'packages' : {
                             'conda_install' : CONDA_DEFAULT_LIST + CONDA_ML_SET, 
                             'pip_install' : PIP_DEFAULT_LIST + PIP_ML_SET, 
                             'pip_upgrade' : PIP_DEFAULT_UPGRADE_LIST}}, 
            'opt' : {'pythonvers' : ["2.7"], 
                         'packages' : {
                             'conda_install' : CONDA_DEFAULT_LIST + CONDA_OPT_SET, 
                             'pip_install' : PIP_DEFAULT_LIST + PIP_OPT_SET, 
                             'pip_upgrade' : PIP_DEFAULT_UPGRADE_LIST }}, 

            'solar' : {'pythonvers' : ["2.7"], 
                         'packages' : {
                             'conda_install' : CONDA_DEFAULT_LIST + ['astropy'],
                             'pip_install' : PIP_DEFAULT_LIST, 
                             'pip_upgrade' : PIP_DEFAULT_UPGRADE_LIST }},
            'solartest' : {'pythonvers' : ["2.7"], 
                         'packages' : {
                             'conda_install' : CONDA_DEFAULT_LIST + ['astropy', 'pyparsing', 'cycler', 'scipy'],
                             'conda_force' : ['scikit-image', 'matplotlib'], 
                             'pip_install' : PIP_DEFAULT_LIST, 
                             'pip_upgrade' : PIP_DEFAULT_UPGRADE_LIST }}

}



CONDA_TEST_STRS = {'numpy' : "__import__('numpy')", 
                   'pytest' : "__import__('pytest')", 
                   "numba" : "__import__('numba')", 
                   "boto3" : "__import__('boto3')", 
                   "PyYAML" : "__import__('yaml')", 
                   "boto" : "__import__('boto')", 
                   "scipy" : "__import__('scipy')", 
                   "pillow" : "__import__('PIL.Image')", 
                   "cvxopt" : "__import__('cvxopt')", 
                   "scikit-image" : "__import__('skimage')", 
                   "scikit-learn" : "__import__('sklearn')"}
PIP_TEST_STRS = {"glob2" : "__import__('glob2')", 
                 "cvxpy" : "__import__('cvxpy')", 
                 "redis" : "__import__('redis')", 
                 "certifi": "__import__('certifi')"}

S3_BUCKET = "s3://ericmjonas-public"
S3URL_STAGING_BASE = S3_BUCKET + "/pywren.runtime.staging"
S3URL_BASE = S3_BUCKET + "/pywren.runtime"


def hash_s3_key(s):
    """
    MD5-hash the contents of an S3 key to enable good partitioning.
    used for sharding the runtimes
    """
    DIGEST_LEN = 6
    m = hashlib.md5()
    m.update(s.encode('ascii'))
    digest = m.hexdigest()
    return "{}-{}".format(digest[:DIGEST_LEN], s)

def get_s3_shard(key, shard_num):
    return "{}.{:04d}".format(key, shard_num)

def split_s3_url(s3_url):
    if s3_url[:5] != "s3://":
        raise ValueError("URL {} is not valid".format(s3_url))


    splits = s3_url[5:].split("/")
    bucket_name = splits[0]
    key = "/".join(splits[1:])
    return bucket_name, key

def merge_runtime_configs(config_list):

    dest_rc = copy.deepcopy(config_list[0])
    if 'conda' not in dest_rc:
        dest_rc['conda'] = {}
    if 'install' not in dest_rc['conda']:
        dest_rc['conda']['install'] = []
    if 'force' not in dest_rc['conda']:
        dest_rc['conda']['force'] = []

    if 'pip' not in dest_rc:
        dest_rc['pip'] = {}
    if 'install' not in dest_rc['pip']:
        dest_rc['pip']['install'] = []
    if 'upgrade' not in dest_rc['pip']:
        dest_rc['pip']['upgrade'] = []
    if 'extracmds' not in dest_rc:
        dest_rc['extracmds'] = []

    
    for c in config_list[1:]:
        if 'conda' in c:
            print dest_rc['conda']['install'], c['conda'].get('install', [])
            dest_rc['conda']['install'] += c['conda'].get('install', [])
            dest_rc['conda']['force'] += c['conda'].get('force', [])
        if 'pip' in c:
            dest_rc['pip']['install'] += c['pip'].get('install', [])
            dest_rc['pip']['upgrade'] += c['pip'].get('upgrade', [])
        dest_rc['extracmds'] += c.get('extracmds', [])

    return dest_rc

def load_runtime_config(filename):
    runtime_config = yaml.load(open(filename, 'r'))
    pythonver = runtime_config['pythonver']
    if not isinstance(pythonver, str):
        raise Exception("pythonver must be a string, not a {}".format(type(pythonver)))

    # merge any includes
    all_configs = [runtime_config]
    for include_file in runtime_config.get('include', []):
        include_dir = os.path.dirname(filename)
        include_path = os.path.join(include_dir, include_file)

        included_config = load_runtime_config(include_path)
        all_configs.append(included_config)
    runtime_config_agg = merge_runtime_configs(all_configs)

    return runtime_config_agg
