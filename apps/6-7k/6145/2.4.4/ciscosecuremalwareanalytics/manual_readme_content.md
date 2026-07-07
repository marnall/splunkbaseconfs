## Backward compatibility

- The value for the ' **vm** ' parameter in the ' **detonate file** ' action is dynamic, so that
  the dropdown is removed from it. The list of available VMs can change from the Cisco Secure Malware Analytics side.
  Run the ' **list vms** ' action to get the valid values for the ' **vm** ' parameter.
- Some action data paths have been added/updated. Hence, it is requested to the end-user to please
  update their existing playbooks by re-inserting | modifying | deleting the corresponding
  action blocks.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Cisco Secure Malware Analytics server. Below are the
default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |
