FROM --platform=linux/arm64 python:3.7.17-slim-bullseye@sha256:603879aeff06df23f0d392a19f7ce02aa85e14e6b4d25fd9647b116e0cb93467
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 TF_NUM_INTRAOP_THREADS=1 TF_NUM_INTEROP_THREADS=1 PYTHONUNBUFFERED=1
RUN printf 'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20230612T000000Z bullseye main\n' > /etc/apt/sources.list && apt-get update && apt-get install -y --no-install-recommends build-essential gfortran libopenblas-dev libhdf5-dev libopenmpi-dev libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN python -m pip install pip==23.0.1 setuptools==59.8.0 wheel==0.42.0 Cython==0.29.37
RUN python -m pip wheel --no-build-isolation --no-deps numpy==1.18.5 -w /wheelhouse && python -m pip install --no-index --find-links=/wheelhouse numpy==1.18.5
RUN python -m pip install cmake==3.27.9 scikit-build==0.17.6
ENV CMAKE_BUILD_PARALLEL_LEVEL=4
COPY requirements.in /experiment/requirements.in
COPY artifacts/tensorflow-1.15.5-cp37-cp37m-linux_aarch64.whl /wheelhouse/
RUN --mount=type=cache,target=/root/.cache/pip echo '3002e4e405b3c7d6c0453304aa40fd64353ffefa03e5b99ad72242' >/dev/null; python -m pip wheel --no-build-isolation --no-deps --find-links=/wheelhouse -r /experiment/requirements.in /wheelhouse/tensorflow-1.15.5-cp37-cp37m-linux_aarch64.whl -w /wheelhouse
RUN python -m pip install --no-index --find-links=/wheelhouse -r /experiment/requirements.in tensorflow==1.15.5 && python -m pip check
WORKDIR /experiment
