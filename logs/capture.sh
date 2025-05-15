#!/bin/bash

set -e

WKDIR=$(dirname $(realpath $0))../../robosapiens-adaptive-platform-turtlebot
HWDIR="$WKDIR/maple-loops/HelloWorld"
DOCKERDIR="$WKDIR/docker"
NOW=$(date +"%Y-%m-%d_%H-%M-%S")

DST_DIR=$(dirname $(realpath $0))/$2_$NOW

LOG_FILE_NAME="MAPE_test.log"
SRC_LOG=$HWDIR/$LOG_FILE_NAME
DST_LOG=$DST_DIR/MAPE.log
DST_LOLA=$DST_DIR/MAPE.input

if [ ! -d ${DST_DIR} ]; then
    mkdir -vp ${DST_DIR}
fi

PREV_PWD=$PWD

if test -f "$SRC_LOG"; then
    echo "Backing up previous MAPE log"
    mv $SRC_LOG $SRC_LOG.bak-$NOW
fi

cd $DOCKERDIR
DEVCONTAINER=devfullmesatb3

echo "Restarting the simulation"
docker compose stop simdeploymesatb3
docker compose up -d simdeploymesatb3

read -p "Now, start the devcontainer, then press enter to continue"

echo "Starting main in Docker"
docker compose exec $DEVCONTAINER bash -c "cd /ws/maple-loops/HelloWorld && python3 main.py"

cd $PREV_PWD

echo "Moving log file"
mv -v $SRC_LOG $DST_LOG

echo "Converting to LOLA"
python log_to_lola.py $DST_LOG $DST_LOLA $1

echo "Running TWC"
CMD="docker run --network host -it --rm -e RUST_BACKTRACE=full -v $HWDIR/LOLA_specs:/mnt/host_models -v $DST_DIR:/mnt/host_input localhost/trustworthiness-checker /mnt/host_models/$3 --input-file /mnt/host_input/MAPE.input"

echo $CMD

$CMD 2>&1 | tee -a "$DST_DIR/TWC-output.txt"
