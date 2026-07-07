BLOCK_IP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<section name="{section_name}" type="LAYER3">
    <rule disabled="false" logged="true">
        <action>deny</action>
        <appliedToList>
            <appliedTo>
                <name>DISTRIBUTED_FIREWALL</name>
                <value>DISTRIBUTED_FIREWALL</value>
                <type>DISTRIBUTED_FIREWALL</type>
                <isValid>true</isValid>
            </appliedTo>
        </appliedToList>
        <destinations excluded="false">
            <destination>
                <value>{ip_to_block}</value>
                <type>Ipv4Address</type>
                <isValid>true</isValid>
            </destination>
        </destinations>
        <direction>inout</direction>
        <packetType>any</packetType>
        <tag>DST-BLOCK</tag>
    </rule>
    <rule disabled="false" logged="true">
        <action>deny</action>
        <appliedToList>
            <appliedTo>
                <name>DISTRIBUTED_FIREWALL</name>
                <value>DISTRIBUTED_FIREWALL</value>
                <type>DISTRIBUTED_FIREWALL</type>
                <isValid>true</isValid>
            </appliedTo>
        </appliedToList>
        <sources excluded="false">
            <source>
                <value>{ip_to_block}</value>
                <type>Ipv4Address</type>
                <isValid>true</isValid>
            </source>
        </sources>
        <direction>inout</direction>
        <packetType>any</packetType>
        <tag>SRC-Block</tag>
    </rule>
</section>
"""

BLOCK_PORT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<section name="{section_name}" type="LAYER3">
    <rule disabled="false" logged="true">
        <action>deny</action>
        <appliedToList>
            <appliedTo>
                <name>DISTRIBUTED_FIREWALL</name>
                <value>DISTRIBUTED_FIREWALL</value>
                <type>DISTRIBUTED_FIREWALL</type>
                <isValid>true</isValid>
            </appliedTo>
        </appliedToList>
        <destinations excluded="false">
            <destination>
                <value>{ip_to_block}</value>
                <type>Ipv4Address</type>
                <isValid>true</isValid>
            </destination>
        </destinations>
        <services>
            <service>
            <destinationPort>{port_to_block}</destinationPort>
            <protocol>{protocol_to_block}</protocol>
            <subProtocol>{protocol_to_block}</subProtocol>
            <isValid>true</isValid>
            </service>
        </services>
        <direction>inout</direction>
        <packetType>any</packetType>
        <tag>DST-BLOCK</tag>
    </rule>
    <rule disabled="false" logged="true">
        <action>deny</action>
        <appliedToList>
            <appliedTo>
                <name>DISTRIBUTED_FIREWALL</name>
                <value>DISTRIBUTED_FIREWALL</value>
                <type>DISTRIBUTED_FIREWALL</type>
                <isValid>true</isValid>
            </appliedTo>
        </appliedToList>
        <sources excluded="false">
            <source>
                <value>{ip_to_block}</value>
                <type>Ipv4Address</type>
                <isValid>true</isValid>
            </source>
        </sources>
        <services>
            <service>
            <destinationPort>{port_to_block}</destinationPort>
            <protocol>{protocol_to_block}</protocol>
            <subProtocol>{protocol_to_block}</subProtocol>
            <isValid>true</isValid>
            </service>
        </services>
        <direction>inout</direction>
        <packetType>any</packetType>
        <tag>SRC-Block</tag>
    </rule>
</section>
"""
CREATE_SECURITY_TAG_XML = """<?xml version="1.0" encoding="UTF-8"?>
<securityTag>
   <objectTypeName>SecurityTag</objectTypeName>
   <type>
      <typeName>SecurityTag</typeName>
   </type>
   <name>{tag_to_create}</name>
   <isUniversal>false</isUniversal>
   <description>Security Tag Created By Phantom</description>
   <extendedAttributes></extendedAttributes>
</securityTag>
"""

CREATE_SECURITY_GROUP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<securitygroup>
  <objectTypeName>SecurityGroup</objectTypeName>
  <type>
         <typeName>SecurityGroup</typeName>
  </type>
  <name>{group_to_create}</name>
  <isUniversal>false</isUniversal>
  <description>Security Group Created By Phantom</description>
  <extendedAttributes></extendedAttributes>
</securitygroup>
"""

TAG_TO_ATTACH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<securityTagAssignment>
    <tagParameter>
         <key>vmname</key>
    </tagParameter>
</securityTagAssignment>
"""

BLOCK_GROUP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<section name="{section_name}" type="LAYER3">
    <rule disabled="false" logged="true">
        <action>deny</action>
        <appliedToList>
            <appliedTo>
                <name>DISTRIBUTED_FIREWALL</name>
                <value>DISTRIBUTED_FIREWALL</value>
                <type>DISTRIBUTED_FIREWALL</type>
                <isValid>true</isValid>
            </appliedTo>
        </appliedToList>
        <destinations excluded="false">
            <destination>
                <value>{group_to_block_id}</value>
                <type>SecurityGroup</type>
                <isValid>true</isValid>
            </destination>
        </destinations>
        <direction>inout</direction>
        <packetType>any</packetType>
        <tag>DST-BLOCK</tag>
    </rule>
    <rule disabled="false" logged="true">
        <action>deny</action>
        <appliedToList>
            <appliedTo>
                <name>DISTRIBUTED_FIREWALL</name>
                <value>DISTRIBUTED_FIREWALL</value>
                <type>DISTRIBUTED_FIREWALL</type>
                <isValid>true</isValid>
            </appliedTo>
        </appliedToList>
        <sources excluded="false">
            <source>
                <value>{group_to_block_id}</value>
                <type>SecurityGroup</type>
                <isValid>true</isValid>
            </source>
        </sources>
        <direction>inout</direction>
        <packetType>any</packetType>
        <tag>SRC-Block</tag>
    </rule>
</section>
"""

GET_ATTACH_XML = """<?xml version="1.0" encoding="UTF-8"?>"""
