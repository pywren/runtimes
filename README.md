# PyWren runtime builders

Forked from [PyWren/runtimes](https://github.com/pywren/runtimes).
Rebuilt, to be executed locally on a docker container.

To build and upload all the runtimes in `runtimes.py` on your docker container:

1. Modify `S3_BUCKET` & `S3URL_BASE = S3_BUCKET + "/pywren.runtime"`, so that they fit your `.pywren_config`-runtime.
2. Change the dependencies in `runtimes.py` to whatever is required.
3. Build the docker image `docker build -t runtimes .` from the base of this repository.
4. Run the docker image `docker run -it runtimes bash`.
5. Expose your AWS credentials in the container (e.g. `export AWS_ACCESS_KEY_ID=...` & `export AWS_SECRET_ACCESS_KEY=...`).
6. Run `python3 builder.py` from `/var/runtime`.

Works with `amazonlinux:2023.0.20230607.0`.
