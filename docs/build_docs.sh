docker build -f Dockerfile . -t sphinx
docker run --rm -v $(pwd):/docs sphinx make clean
docker run --rm -v $(pwd):/docs sphinx make html
chmod -R 777 build/html
