docker build -f Dockerfile . -t sphinx
docker run --rm -v $(pwd):/docs sphinx make html
