# Add on for Cilium Hubble Flows

Cilium is a CNI for Kubernetes. It is able to monitor traffic like a firewall between containers inside a Kubernetes Cluster using Network Policies.  
Logs can be generated and saved using the Hubble exporter.

To configure Cilium Hubble flows logs, please refer to
[docs.cilium.io/en/stable/observability/hubble-exporter/#configuring-hubble-exporter](https://docs.cilium.io/en/stable/observability/hubble-exporter/#configuring-hubble-exporter)  

The following is an exemple of a configuration using helm values to configure recommanded fields:
```yaml
hubble:
  export:
    # --- Defines max file size of output file before it gets rotated.
    fileMaxSizeMb: 10
    # --- Defines max number of backup/rotated files.
    fileMaxBackups: 10
    # --- Static exporter configuration.
    # Static exporter is bound to agent lifecycle.
    static:
      enabled: true
      filePath: /var/run/cilium/hubble/events.log
      denyList: []
      fieldMask: 
        - time
        - source.identity
        - source.namespace
        - source.pod_name
        - destination.identity
        - destination.namespace
        - destination.pod_name
        - source_service
        - destination_service
        - destination_names
        - l4.TCP.destination_port
        - l4.TCP.source_port
        - IP
        - ethernet
        - l7
        - flow.l7.dns.query
        - traffic_direction
        - Type
        - node_name
        - is_reply
        - event_type
        - verdict
```
This configuration is static, and need a restart of cilium pods for effect.
From the documentation:
> Standard hubble exporter configuration accepts only one set of filters and requires cilium pod restart to change config. Dynamic flow logs allow configuring multiple filters at the same time and saving output in separate files. Additionally it does not require cilium pod restarts to apply changed configuration.


The following describes fields in details [github.com/cilium/cilium/blob/main/api/v1/flow/flow.proto](https://github.com/cilium/cilium/blob/main/api/v1/flow/flow.proto) 

The table below describe the following sourcetypes available:

|format|type|sourcetype|
|--|--|--|
| json | network | cilium:hubble:flow |

Available Fields (in JSON) for network logs

|Raw Field|Splunk field|Description|Exemple|
| -- | -- | -- | -- |
|time|_time|The time at which network request happened.|2024-05-11T10:01:54.222646154Z|
|uuid|-|Unique Id for the network request|3822803d-be6a-48c1-8ed6-ea36de7b506d|
|flow.verdict|action|Action taken by Cilium policy|DROPPED|
|drop_reason|-|-|313|
|flow.ethernet.source|src_mac|Source Mac of the pod doing the request|72:ff:7c:1e:2f:d5|
|flow.ethernet.destination|dest_mac|Destination Mac of the pod contacted|e2:23:c6:05:02:04|
|flow.IP.source|src_ip|Source IP of the pod doing the request|10.0.2.22|
|flow.IP.destination|dest_ip|Destination IP of the pod contacted|10.0.3.2|
|flow.IP.ipVersion |-|IP Version|IPv4|
|flow.l4.TCP.source_port|src_port|Source Port used by the the pod doing the request|37422|
|flow.l4.TCP.destination_port|dest_port|Destination port of the pod contacted|443|
|flow.l4.UDP.source_port|src_port|Source Port used by the the pod doing the request|37422|
|flow.l4.UDP.destination_port|dest_port|Destination port of the pod contacted|443|
|flow.l4.TCP.flags.SYN|-|Is it the SYN flags|true|
|flow.l4.TCP.flags.ACK|-|Is it the ACK flags|true|
|flow.l4.TCP.flags.PSH|-|Is it the PSH flags|true|
|flow.l7.dns.cnames{}|-|Array of CNames|['front-azure.XXX.XX']|
|flow.l7.dns.ips{}|-|Array of IP in the response|['20.XX.XXX.179']|
|flow.l7.dns.observation_source|-|FIXME|proxy|
|flow.l7.dns.qtypes{}|-|DNS entry types (A, AAAA)|['AAAA']|
|flow.l7.dns.query|-|DNS query|gitlab.com.|	
|flow.l7.dns.rcode|-|FIXME|3|
|flow.l7.dns.rrtypes{}|-|Array of DNS entry types (A, AAAA, CNAME)|['A']|
|flow.l7.dns.ttl|-|TTL of the DNS response|30|
|flow.l7.type|-|REQUEST or RESPONSE|REQUEST|
|flow.source.ID|-|ID of the source flow|834|
|flow.source.identity|-|Cilium Identity|15476|
|flow.source.namespace|-|Namespace of the pod doing the request|traefik|
|flow.source.labels|-|Array of labels for the source pod|["k8s:app.kubernetes.io/name=traefik",...]|
|flow.source.pod_name|-|Name of the pod doing the request|traefik-b4c588c9-grw7r|
|flow.source.workloads{}.name|-|Name of the source Workload|traefik|
|flow.source.workloads{}.kind|-|Kind of source workload (Deployment,StatefulSet,DaemonSet)|Deployment|
|flow.destination.ID|-|ID of the source flow|82|
|flow.destination.identity|-|Cilium Identity|15|
|flow.destination.namespace|-|Namespace of the pod contacted|crowdsec|
|flow.destination.pod_name|-|Name of the pod contacted|crowdsec-lapi-23d23c0-zdw2e|
|flow.destination.workloads{}.name|-|Name of the destination Workload|crowdsec-lapi|
|flow.destination.workloads{}.kind|-|Kind of destination workload (Deployment,StatefulSet,DaemonSet)|Deployment|
|flow.Type|-|FIXME|L3_L4|
|flow.node_name|-|Name of the Node where is located the pod doing the request|k8s_node_0|
|flow.destination_names|-|array of FQDN contacted|["traefik.io"]|
|flow.traffic_direction|-|Direction of the taffic|EGRESS|
|flow.is_reply|-|Is the request a response|true|
|flow.drop_reason_desc|-|Description of the DROPPED reason|POLICY_DENIED|


In case of any problem with the addon please open an issue at [gitlab.com/mathieuHa/splunk_cilium_addon](https://gitlab.com/mathieuHa/splunk_cilium_addon)

Mathieu HANOTAUX