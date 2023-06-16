"""
fab -f fabfile_builer.py -R builder conda_setup_mkl conda_clean package_all


"""
import json
import pickle
import json
import runtimes
import yaml
import os
import subprocess

def tags_to_dict(d):
    return {a['Key'] : a['Value'] for a in d}

def shrink_conda(conda_base_dir ,CONDA_RUNTIME_DIR):
    os.system("python3.7 shrinkconda.py {} {}".format(conda_base_dir, CONDA_RUNTIME_DIR))


CONDA_BUILD_DIR = "/tmp/conda"
CONDA_INSTALL_DIR = "/tmp/conda/envs"


def create_runtime(pythonver,
                   conda_packages, pip_packages,
                   pip_upgrade_packages, conda_env_dir):

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
    old_pwd = os.getcwd()

    os.chdir(CONDA_BUILD_DIR)
    # TODO: Allow multiple package builds (aka change env name)
    env_name = pythonver
    os.system("{}/bin/conda create -y --name {}".format(CONDA_BUILD_DIR, env_name))
    os.system("{}/bin/conda install -n {} -q -y python={}".format(CONDA_BUILD_DIR, env_name, pythonver))
    os.system("{}/bin/conda install -n {} -q -y {}".format(CONDA_BUILD_DIR, env_name, conda_default_pkg_str))
    for chan, pkg in conda_pkgs_custom_channel:
        os.system("{}/bin/conda install -n {} -q -y -c {} {}".format(CONDA_BUILD_DIR, env_name, chan, pkg))
    os.system("{}/bin/pip install {}".format(conda_env_dir, pip_pkg_str))
    os.system("{}/bin/pip install --upgrade {}".format(conda_env_dir, pip_pkg_upgrade_str))
    os.chdir(old_pwd)

def format_freeze_str(x):
    packages = x.splitlines()
    return [a.split("==") for a in packages]

def package_all(s3url, env_install_dir):
    old_cwd = os.getcwd()

    os.chdir(env_install_dir)
    os.system("tar czf {} *".format(os.path.join(CONDA_BUILD_DIR, 'condaruntime.tar.gz')))

    os.system("aws s3 cp {} {}".format(os.path.join(CONDA_BUILD_DIR, 'condaruntime.tar.gz'), s3url))
    os.chdir(old_cwd)

def build_and_stage_runtime(runtime_name, runtime_config):
        python_ver = runtime_config['pythonver']
        conda_install = runtime_config['conda_install']
        pip_install = runtime_config['pip_install']
        pip_upgrade = runtime_config['pip_upgrade']

        env_name = python_ver
        env_install_dir = CONDA_INSTALL_DIR + "/" + env_name
        create_runtime(python_ver, conda_install,
                pip_install, pip_upgrade, env_install_dir)
        shrink_conda(CONDA_BUILD_DIR ,env_install_dir)
        freeze_str = get_runtime_pip_freeze(env_install_dir)

        freeze_pkgs = format_freeze_str(freeze_str)

        preinstalls_str = get_preinstalls(env_install_dir)
        preinstalls = json.loads(preinstalls_str)
        conda_env_yaml = get_conda_root_env(CONDA_BUILD_DIR, env_name)
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

        package_all(runtime_tar_gz, env_install_dir)
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

def get_runtime_pip_freeze(conda_env_install_dir):
    out = subprocess.run(["{}/bin/pip".format(conda_env_install_dir), "list", "--format=freeze"], stderr=subprocess.DEVNULL, stdout=subprocess.PIPE)
    return out.stdout.decode("utf-8")

def get_preinstalls(conda_env_install_dir):
    out = subprocess.run(["{}/bin/python".format(conda_env_install_dir),"-c", "import pkgutil;import json;print(json.dumps([(mod, is_pkg) for _, mod, is_pkg in pkgutil.iter_modules()]))"],stdout=subprocess.PIPE)
    return out.stdout.decode("utf-8")

def get_conda_root_env(conda_base_dir, env_name):
    out = subprocess.run(["{}/bin/conda".format(conda_base_dir), "env", "export", "-n", env_name], stderr=subprocess.DEVNULL,stdout=subprocess.PIPE)
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