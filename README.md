PyWren runtime builders

To build all the runtimes in `runtimes.py` on the aws machine
`builder` and put them on the staging server:

```
fab -f fabfile_builder.py -R builder build_all_runtimes
```

To test, push the repo to github, which will trigger a travis build pointing
at the staged runtimes.

To deploy them and shard them, do this:

```
fab -f fabfile_builder.py -R builder deploy_runtimes:num_shards=50
```

```
docker-compose run -e S3_BUCKET=... amazonlinux2.7 fab -f fabfile_builder.py build_single_runtime:runtime_name=minimal,pythonver=3.4
```

```
fab -f fabfile_builder.py build_single_runtime:runtime_name=minimal,pythonver=3.4
```

```
fab -f fabfile_builder.py build_single_runtime:runtime_name=minimal,pythonver=3.6
```

```
fab -f fabfile_builder.py get_preinstalls:conda_install_dir=/tmp/condaruntime

from fabfile_builder import build_single_runtime

runtime_name = 'minimal'
python_ver = '3.4'
build_single_runtime(runtime_name, python_ver)


runtime_name = 'minimal'
python_ver = '3.4'
runtimes.get_staged_runtime_url(runtime_name, python_ver)

runtimes.get_runtime_url_from_staging(runtime_name, python_ver)
staging_runtime_tar_gz, staging_runtime_meta_json \
    = runtimes.get_staged_runtime_url(runtime_name, python_ver)

base_tar_gz = runtimes.get_runtime_url_from_staging(staging_runtime_tar_gz)
```
