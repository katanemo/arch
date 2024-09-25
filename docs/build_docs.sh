docker build -f Dockerfile . -t sphinx
docker run --rm -v ./:/docs sphinx make html
