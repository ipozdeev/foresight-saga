FROM jupyter/scipy-notebook

COPY environment.yml tmp/

RUN mamba env create -f tmp/environment.yml 

RUN /opt/conda/envs/foresight-saga/bin/python -m ipykernel install --user --name foresight-saga