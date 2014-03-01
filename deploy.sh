SERVER="furic.pw"
USER="anders"
PORT="45118"
DIRECTORY="/home/anders/KTN_Fellesprosjekt/"

git checkout master

scp -P $PORT server.py $USER@$SERVER:$DIRECTORY"master/"
scp -P $PORT Message.py $USER@$SERVER:$DIRECTORY"master/"

git checkout Experimental

scp -P $PORT server.py $USER@$SERVER:$DIRECTORY"Experimental/server.py"
scp -P $PORT Message.py $USER@$SERVER:$DIRECTORY"Experimental/Message.py"