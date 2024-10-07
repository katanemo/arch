docker build -f Dockerfile . -t sphinx
docker run --user $(id -u):$(id -g) --rm -v $(pwd):/docs sphinx make clean
docker run --user $(id -u):$(id -g) --rm -v $(pwd):/docs sphinx make html
chmod -R 777 build/html
