docker rm $(docker ps -aq) -f
git reset --hard HEAD
git pull origin develop
./docker-build.sh