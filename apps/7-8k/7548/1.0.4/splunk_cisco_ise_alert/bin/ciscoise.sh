#!/bin/bash
if [[ "$1" == "--execute" ]]; then
    read sessionKey
    URL=$(echo $sessionKey | jq .configuration.url | sed 's/"//g')
    MAC=$(echo $sessionKey | jq .configuration.mac | sed 's/"//g')
    USER=$(echo $sessionKey | jq .configuration.username | sed 's/"//g')
    PASSWORD=$(echo $sessionKey | jq .configuration.password | sed 's/"//g')
fi

curl -ks --location --request PUT ${URL} --header "Content-type: application/json" --header "ERS-Media-Type: anc.ancendpoint.1.0" --header "Accept: application/json" --data "{ \"OperationAdditionalData\": { \"additionalData\": [ { \"name\": \"macAddress\", \"value\": \"${MAC}\" }, { \"name\": \"policyName\", \"value\": \"Quarantine\" } ] } }" -u ${USER}:${PASSWORD}
