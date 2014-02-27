SERVER="furic.pw"
USER="anders"
PORT="45118"
DIRECTORY="/home/anders/"

scp -P $PORT server.py $USER@$SERVER:$DIRECTORY
scp -P $PORT Message.py $USER@$SERVER:$DIRECTORY
