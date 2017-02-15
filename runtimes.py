
CONDA_DEFAULT_LIST = ["tblib", 
                      "numpy", 
                      "pytest", 
                      "Click", 
                      "numba", 
                      "boto3", 
                      "PyYAML", 
                      "cython", 
                      "boto"]

PIP_DEFAULT_LIST = ['glob2']
PIP_DEFAULT_UPGRADE_LIST = ['cloudpickle', 'enum34']

CONDA_ML_SET = ['scipy', 'pillow', 'cvxopt', 'scikit-learn']
PIP_ML_SET = ['cvxpy', 'redis']

RUNTIMES = {'minimal_2' : (2, CONDA_DEFAULT_LIST, 
                         PIP_DEFAULT_LIST, 
                         PIP_DEFAULT_UPGRADE_LIST),
            'minimal_3' : (3, CONDA_DEFAULT_LIST, 
                           PIP_DEFAULT_LIST, 
                           PIP_DEFAULT_UPGRADE_LIST), 
            'ml_2' : (2, CONDA_DEFAULT_LIST  + CONDA_ML_SET, 
                      PIP_DEFAULT_LIST + PIP_ML_SET, 
                      PIP_DEFAULT_UPGRADE_LIST),
            'ml_3' : (3, CONDA_DEFAULT_LIST + CONDA_ML_SET, 
                           PIP_DEFAULT_LIST + PIP_ML_SET, 
                           PIP_DEFAULT_UPGRADE_LIST), 

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
                 "redis" : "__import__('redis"}


S3URL_BASE = "s3://ericmjonas-public/pywren.runtime.staging"

def get_staged_runtime_url(runtime_name, runtime_python_version):
    s3url = "{}/pywren_runtime-{}-{}".format(S3URL_BASE, 
                                             runtime_python_version, runtime_name)

    return  s3url + ".tar.gz", s3url + "meta.json"
