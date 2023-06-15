"""
fab -f fabfile_builer.py -R builder conda_setup_mkl conda_clean package_all


"""
import boto3
import cloudpickle
import json
import base64
import pickle
import json
import runtimes
import yaml
import os
import subprocess

def tags_to_dict(d):
    return {a['Key'] : a['Value'] for a in d}

def install_gist():
    """
    https://github.com/yuichiroTCY/lear-gist-python
    """
    old_pwd = os.getcwd()

    os.chdir("/tmp")
    os.system("yum install -q -y  git gcc g++ make") # might have to execute with sudo
    os.system("rm -Rf gist")
    os.system("mkdir gist")

    os.chdir("gist")
    os.system("git clone https://github.com/yuichiroTCY/lear-gist-python")

    os.chdir("lear-gist-python")
    os.system("/tmp/conda/condaruntime/bin/conda install -q -y -c menpo fftw=3.3.4")
    os.system("sh download-lear.sh")
    os.system("sed -i '1s/^/#define M_PI 3.1415926535897\\n /' lear_gist-1.2/gist.c")
    os.system("CFLAGS=-std=c99 /tmp/conda/condaruntime/bin/python setup.py build_ext -I /tmp/conda/condaruntime/include/ -L /tmp/conda/condaruntime/lib/")
    os.system("CFLAGS=-std=c99 /tmp/conda/condaruntime/bin/python setup.py install")
    os.chdir(old_pwd)

def shrink_conda(CONDA_RUNTIME_DIR):
    os.system("python3.7 shrinkconda.py {}".format(CONDA_RUNTIME_DIR))



CONDA_BUILD_DIR = "/tmp/conda"
CONDA_INSTALL_DIR = "/tmp/condaruntime"


def create_runtime(pythonver,
                   conda_packages, pip_packages,
                   pip_upgrade_packages):

    conda_pkgs_default_channel = []
    conda_pkgs_custom_channel = []
    for c in conda_packages:
        if isinstance(c, tuple):
            conda_pkgs_custom_channel.append(c)
        else:
            conda_pkgs_default_channel.append(c)

    conda_default_pkg_str = " ".join(conda_pkgs_default_channel)
    pip_pkg_str = " ".join(pip_packages)
    pip_pkg_upgrade_str = " ".join(pip_upgrade_packages)
    python_base_ver = pythonver.split(".")[0]
    os.system("rm -Rf {}".format(CONDA_BUILD_DIR))
    os.system("rm -Rf {}".format(CONDA_INSTALL_DIR))
    os.system("mkdir -p {}".format(CONDA_BUILD_DIR))
    old_pwd = os.getcwd()

    os.chdir(CONDA_BUILD_DIR)
    os.system("wget https://repo.continuum.io/miniconda/Miniconda{}-latest-Linux-x86_64.sh -O miniconda.sh ".format(python_base_ver))
    os.system("bash miniconda.sh -b -p {}".format(CONDA_INSTALL_DIR))
    os.system("{}/bin/conda install -q -y python={}".format(CONDA_INSTALL_DIR,pythonver))
    os.system("{}/bin/conda install -q -y {}".format(CONDA_INSTALL_DIR,conda_default_pkg_str))
    for chan, pkg in conda_pkgs_custom_channel:
        os.system("{}/bin/conda install -q -y -c {} {}".format(CONDA_INSTALL_DIR, chan, pkg))
    os.system("{}/bin/pip install {}".format(CONDA_INSTALL_DIR, pip_pkg_str))
    os.system("{}/bin/pip install --upgrade {}".format(CONDA_INSTALL_DIR, pip_pkg_upgrade_str))
    os.chdir(old_pwd)

def format_freeze_str(x):
    packages = x.splitlines()
    return [a.split("==") for a in packages]

def package_all(s3url):
    old_cwd = os.getcwd()

    os.chdir(CONDA_INSTALL_DIR + "/../")
    os.system("tar czf {} condaruntime".format(os.path.join(CONDA_BUILD_DIR, 'condaruntime.tar.gz')))

    os.system("aws s3 cp {} {}".format(os.path.join(CONDA_BUILD_DIR, 'condaruntime.tar.gz'), s3url))
    os.chdir(old_cwd)

def build_and_stage_runtime(runtime_name, runtime_config):
        python_ver = runtime_config['pythonver']
        conda_install = runtime_config['conda_install']
        pip_install = runtime_config['pip_install']
        pip_upgrade = runtime_config['pip_upgrade']
        create_runtime(python_ver, conda_install,
                pip_install, pip_upgrade)
        shrink_conda(CONDA_INSTALL_DIR)
        freeze_str = get_runtime_pip_freeze(CONDA_INSTALL_DIR)

        freeze_pkgs = format_freeze_str(freeze_str)

        preinstalls_str = get_preinstalls(CONDA_INSTALL_DIR)
        preinstalls = json.loads(preinstalls_str)
        conda_env_yaml = get_conda_root_env(CONDA_INSTALL_DIR)
        pickle.dump(conda_env_yaml, open("debug.pickle", 'wb'))
        conda_env = yaml.load(conda_env_yaml, yaml.Loader)
        runtime_dict = {'python_ver' : python_ver,
                        'conda_install' : conda_install,
                        'pip_install' : pip_install,
                        'pip_upgrade' : pip_upgrade,
                        'pkg_ver_list' : freeze_pkgs,
                        'preinstalls' : preinstalls,
                        'conda_env_config': conda_env}

        # Use a single url for staging
        runtime_tar_gz, runtime_meta_json = \
            runtimes.get_staged_runtime_url(runtime_name, python_ver)

        urls = [runtime_tar_gz]
        runtime_dict['urls'] = urls

        package_all(runtime_tar_gz)
        with open('runtime.meta.json', 'w') as outfile:
            json.dump(runtime_dict, outfile)
            outfile.flush()

        os.system("aws s3 cp runtime.meta.json {}".format(runtime_meta_json))

def build_all_runtimes():
    for runtime_name, rc in runtimes.RUNTIMES.items():
        for pythonver in rc['pythonvers']:
            rc2 = rc['packages'].copy()
            rc2['pythonver'] = pythonver
            build_and_stage_runtime(runtime_name, rc2)

def build_single_runtime(runtime_name, pythonver):
    rc = runtimes.RUNTIMES[runtime_name]
    rc2 = rc['packages'].copy()
    rc2['pythonver'] = pythonver
    build_and_stage_runtime(runtime_name, rc2)

def get_runtime_pip_freeze(conda_install_dir):
    out = subprocess.run(["{}/bin/pip".format(conda_install_dir), "list", "--format=freeze"], stderr=subprocess.DEVNULL, stdout=subprocess.PIPE)
    return out.stdout.decode("utf-8")

def get_preinstalls(conda_install_dir):
    out = subprocess.run(["{}/bin/python".format(conda_install_dir),"-c", "import pkgutil;import json;print(json.dumps([(mod, is_pkg) for _, mod, is_pkg in pkgutil.iter_modules()]))"],stdout=subprocess.PIPE)
    return out.stdout.decode("utf-8")

def get_conda_root_env(conda_install_dir):
    out = subprocess.run(["{}/bin/conda".format(conda_install_dir), "env", "export", "-n", "root"], stderr=subprocess.DEVNULL,stdout=subprocess.PIPE)
    return out.stdout.decode("utf-8")

def deploy_runtime(runtime_name, python_ver):
    # move from staging to production
    staging_runtime_tar_gz, staging_runtime_meta_json \
        = runtimes.get_staged_runtime_url(runtime_name, python_ver)

    runtime_tar_gz, runtime_meta_json = runtimes.get_runtime_url(runtime_name,
                                                                 python_ver)

    os.system("aws s3 cp {} {}".format(staging_runtime_tar_gz,
                                   runtime_tar_gz))

    os.system("aws s3 cp {} {}".format(staging_runtime_meta_json,
                                   runtime_meta_json))


def deploy_runtimes(num_shards=10):
    num_shards = int(num_shards)
    for runtime_name, rc in runtimes.RUNTIMES.items():
        for python_ver in rc['pythonvers']:
            staging_runtime_tar_gz, staging_runtime_meta_json \
                = runtimes.get_staged_runtime_url(runtime_name, python_ver)

            # Always upload to the base tar gz url.
            base_tar_gz = runtimes.get_runtime_url_from_staging(staging_runtime_tar_gz)
            os.system("aws s3 cp {} {}".format(staging_runtime_tar_gz,
                                           base_tar_gz))

            runtime_meta_json_url = runtimes.get_runtime_url_from_staging(staging_runtime_meta_json)
            # If required, generate the shard urls and update metadata
            if num_shards > 1:
                os.system("aws s3 cp {} runtime.meta.json".format(staging_runtime_meta_json))
                meta_dict = json.load(open('runtime.meta.json', 'r'))
                shard_urls = []
                for shard_id in xrange(num_shards):
                    bucket_name, key = runtimes.split_s3_url(base_tar_gz)
                    shard_key = runtimes.get_s3_shard(key, shard_id)
                    hash_s3_key = runtimes.hash_s3_key(shard_key)
                    shard_url = "s3://{}/{}".format(bucket_name, hash_s3_key)
                    os.system("aws s3 cp {} {}".format(base_tar_gz,
                                                   shard_url))
                    shard_urls.append(shard_url)

                meta_dict['urls'] = shard_urls
                with open('runtime.meta.json', 'w') as outfile:
                    json.dump(meta_dict, outfile)
                    outfile.flush()
                os.system("aws s3 cp runtime.meta.json {}".format(runtime_meta_json_url))
            else:
                os.system("aws s3 cp {} {}".format(staging_runtime_meta_json,
                                               runtime_meta_json_url))

if __name__ == "__main__":
    build_all_runtimes()