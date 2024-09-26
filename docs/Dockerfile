FROM sphinxdoc/sphinx

WORKDIR /docs
ADD requirements.txt /docs
RUN python3 -m pip install -r requirements.txt
RUN pip freeze
