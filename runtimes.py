
CONDA_DEFAULT_LIST = ["tblib", 
                      "numpy", 
                      "pytest", 
                      "Click", 
                      "numba", 
                      "boto3", 
                      "PyYAML", 
                      "cython"]

PIP_DEFAULT_LIST = ['glob2', 'boto', 'certifi']
PIP_DEFAULT_UPGRADE_LIST = ['cloudpickle', 'enum34']

CONDA_ML_SET = ['scipy', 'pillow', 'cvxopt', 'scikit-learn']
PIP_ML_SET = ['cvxpy', 'redis']

RUNTIMES = {'minimal' : {'pythonvers' : ["2.7", "3.5", "3.6"],  
                         'packages' : { 
                             'conda_install' : CONDA_DEFAULT_LIST, 
                             'pip_install' : PIP_DEFAULT_LIST, 
                             'pip_upgrade' : PIP_DEFAULT_UPGRADE_LIST}},
            'ml' : {'pythonvers' :  ["2.7", "3.5", "3.6"],
                    'packages' : {
                        'conda_install' : CONDA_DEFAULT_LIST + CONDA_ML_SET, 
                        'pip_install' : PIP_DEFAULT_LIST + PIP_ML_SET, 
                        'pip_upgrade' : PIP_DEFAULT_UPGRADE_LIST + PIP_DEFAULT_UPGRADE_LIST}},
            'default' : {'pythonvers' : ["2.7", "3.5", "3.6"], 
                         'packages' : {
                             'conda_install' : CONDA_DEFAULT_LIST + CONDA_ML_SET, 
                             'pip_install' : PIP_DEFAULT_LIST + PIP_ML_SET, 
                             'pip_upgrade' : PIP_DEFAULT_UPGRADE_LIST + PIP_DEFAULT_UPGRADE_LIST}}


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


S3URL_STAGING_BASE = "s3://ericmjonas-public/pywren.runtime.staging"

def get_staged_runtime_url(runtime_name, runtime_python_version):
    s3url = "{}/pywren_runtime-{}-{}".format(S3URL_STAGING_BASE, 
                                             runtime_python_version, runtime_name)

    return  s3url + ".tar.gz", s3url + ".meta.json"

S3URL_BASE = "s3://ericmjonas-public/pywren.runtime"

def get_runtime_url(runtime_name, runtime_python_version):
    s3url = "{}/pywren_runtime-{}-{}".format(S3URL_BASE, 
                                             runtime_python_version, runtime_name)

    return  s3url + ".tar.gz", s3url + ".meta.json"
