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


### For the user simply trying to get a new package

```
pywren-runtime launch-builder
pywren-runtime basic_setup setup.config 
pywren-runtime ssh-builder
pywren-runtime package-runtime
pywren-runtime deploy-runtime
```


What if instead we just focus on using as much of fabric
as possible right now? 
```
fab -f fabfile_builder.py launch
```

Then test our ability to ssh in (wait for instance to come up
```
fab -f fabfile_builder.py -R builder ssh
```

```
fab -f fabfile_builder.py -R builder build_single_runtime:config.yaml
```

```
pythonver: 2.7
miniconda_url: https://repo.continuum.io/miniconda/Miniconda2.7-latest-Linux-x86_64.sh -O miniconda.sh
conda:
    installs:
        - tblib
        - numpy
        - pytest
        - Click
        - boto3
        - PyYAML
        - six
        - cython
        - future
    force:
        - scikit-image
        - matplotlib
pip:
    installs:
        - glob2
        - boto
        - certify
    upgrades:
        - cloudpickle
        - enum34
        
        
```

To deploy a runtime we have a two-stage process:
1. Create a .meta.json with all the metadata about the runtime, 
   including where the tarball will ultimatey be located
2. Create the tarball
3. Upload the tarball someplace, and upload the meta.json

Now this process mostly involves bringing a copy of
the tarball and metadata local. We do this because it's
likely that the remote builder will not have write access
to the eventual deploy location. The downside
is that this means we are potentially copying 500+MB
runtimes around. 



```
fab -f fabfile_builder.py launch
fab -f fabfile_builder.py -R builder ssh
fab -f fabfile_builder.py -R builder build_runtime:config=runtime_configs/default_2.7.yaml 
fab -f fabfile_builder.py -R builder shrink_runtime
fab -f fabfile_builder.py -R builder deploy_runtime:s3_url_base=s3://ericmjonas-public/test-pywren-runtime 
```
