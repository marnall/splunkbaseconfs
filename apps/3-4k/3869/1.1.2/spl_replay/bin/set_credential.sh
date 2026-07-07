#!/bin/bash

echo "Username to store:"
read  user
echo "Password to store:"
read pass

echo "Authorized User:"
read auser

curl -XPOST --tlsv1 -k https://localhost:8089/services/storage/passwords -u $auser -d "output_mode=json" -d "name=$user" -d "realm=spl_replay" -d "password=$pass"