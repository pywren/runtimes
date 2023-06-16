import boto3
import cloudpickle
import json
import base64
import pickle
import os

from builder import shrink_conda

CONDA_BUILD_DIR = "/tmp/conda"
CONDA_INSTALL_DIR = os.path.join(CONDA_BUILD_DIR, "condaruntime")

CONDA_DEFAULT_LIST = ["tblib", "numpy", "pytest", "Click", "numba", "boto3", "PyYAML", "cython", "boto", "scipy", "pillow", "cvxopt", "scikit-learn"]

PIP_DEFAULT_LIST = ['cvxpy', 'redis', 'glob2']
PIP_DEFAULT_UPGRADE_LIST = ['cloudpickle', 'enum34']

def create_runtime(pythonver,
                   conda_packages, pip_packages,
                   pip_upgrade_packages):


    conda_pkg_str = " ".join(conda_packages)
    pip_pkg_str = " ".join(pip_packages)
    pip_pkg_upgrade_str = " ".join(pip_upgrade_packages)
    os.system("rm -Rf {}".format(CONDA_BUILD_DIR))
    os.system("mkdir -p {}".format(CONDA_BUILD_DIR))
    with os.chdir(CONDA_BUILD_DIR):
        os.system("wget https://repo.continuum.io/miniconda/Miniconda{}-latest-Linux-x86_64.sh -O miniconda.sh ".format(pythonver))

        os.system("bash miniconda.sh -b -p {}".format(CONDA_INSTALL_DIR))

        os.system("{}/bin/conda install -q -y {}".format(CONDA_INSTALL_DIR, conda_pkg_str))
        os.system("{}/bin/pip install {}".format(CONDA_INSTALL_DIR, pip_pkg_str))
        os.system("{}/bin/pip install --upgrade {}".format(CONDA_INSTALL_DIR, pip_pkg_upgrade_str))

RUNTIMES = {'keyname' : (3, CONDA_DEFAULT_LIST,
                         PIP_DEFAULT_LIST,
                         PIP_DEFAULT_UPGRADE_LIST)}

def build_runtimes():

    for k, v in RUNTIMES.items():
        create_runtime(v[0], v[1], v[2], v[3])
        shrink_conda(CONDA_INSTALL_DIR)


