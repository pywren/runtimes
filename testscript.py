from __future__ import print_function
"""
Test script to run inside of runtime. Uses whatever version of pywren is installed
"""
import pywren 
import runtimes
import sys
from sklearn import datasets
import numpy as np
import importlib

for runtime_name, runtime_config in runtimes.RUNTIMES.items():
    python_ver = runtime_config[0]
    if sys.version_info.major == python_ver:

        # create an executor
        config = pywren.wrenconfig.default()
        staged_runtime_url, staged_meta_url = runtimes.get_staged_runtime_url(runtime_name, python_ver)
        assert staged_runtime_url[:5] == "s3://"
        splits = staged_runtime_url[5:].split("/")
        bucket = splits[0]
        key = "/".join(splits[1:])
        config['runtime']['bucket'] = bucket
        config['runtime']['s3_key'] = key
        
        wrenexec = pywren.lambda_executor(config)

        def import_check(x):
            results = {}
            
            conda_results = {}
            for pkg in runtime_config[1]:
                if pkg in runtimes.CONDA_TEST_STRS:
                    test_str = runtimes.CONDA_TEST_STRS[pkg]
                    try:
                        eval(test_str)
                        conda_results[pkg] = True
                    except ImportError:
                        conda_results[pkg] = False

            results['conda'] = conda_results
            
            return results
        print("Calling async")
        fut = wrenexec.call_async(import_check, 2)
        print(fut.result())
    else:
        print("skipping runtime config {}".format(runtime_name))
