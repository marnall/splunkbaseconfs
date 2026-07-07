# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

from license import License

# ****************** WARNING: these license hashes and GUIDs are used elsewhere in the code *******************
# If any licenses in this file are updated, then their hashes below should also be updated.
# In addition, these hashes and GUIDs should also be updated in the source code under the following directories:
# apps/SA-ITOA/package/lib/feature_flagging/ 


# Because we shipped ITSI 4.0.0 - 4.5.x with the same license, the guid for the license that we want
# to remove and replace will be the same across deployments or versions
old_itsi_internal_ea_license = License(
    guid='37589432-3563-4467-98D6-79D71CBF1801',
    name='Old ITSI internal license'
)

itsi_internal_license = License(
    name='ITSI General Sourcetype License',
    body='''
    <license>
        <signature>UrBfGVqTyzcpKMr7JDHsEFIVO1RLRWn9dZaKBm5BTRzdz6MIhE1XRf4FJ5JVpUxquLwf1LCkJ4QV78uq4kLClhvWuGPYNaMBmGe9w8MnWQi2TlMeTwwVHNoX6FB3TiNujQj3g+sQsP0IY/TdtV98etDRNwOYIkuLFPap6dhvBIulBkFiBhGI+ELmHV7LRGcVgJYgBF8zpOjVXSQMh0RL+6MWbrVdkKZU5ducxDJcpUEjp0PR3QePtczXm5ZdETui42mtpyiZsMlcYMGmQWS9erKst5EX8R9BSyudZkbZL4uoSVdVv8691Ml1GLb2pbgQQLm/Qwb2XaCk5QNo4Odv4A==</signature>
        <payload>
            <type>fixed-sourcetype</type>
            <group_id>Enterprise</group_id>
            <quota>107374182400000</quota>
            <max_violations>5</max_violations>
            <window_period>30</window_period>
            <creation_time>1594969200</creation_time>
            <label>IT Service Intelligence Internals *DO NOT COPY*</label>
            <expiration_time>2163221999</expiration_time>
            <features>
                <feature>Auth</feature>
                <feature>FwdData</feature>
                <feature>LocalSearch</feature>
                <feature>ScheduledSearch</feature>
                <feature>Alerting</feature>
                <feature>SplunkWeb</feature>
            </features>
            <add_ons>
                <add_on name="itsi" type="app">
                    <parameter key="size" value="1"/>
                </add_on>
            </add_ons>
            <sourcetypes>
                <sourcetype>itsi_*</sourcetype>
            </sourcetypes>
            <guid>2AEECCCF-EDBC-499E-862C-8C79844114D4</guid>
        </payload>
    </license>
    '''
)

plus_suite_signaling_license = License(
    name='ITSI Plus suite signaling license',
    hash='00281640570D92DDCECA2D4BA904476503C8AF47D30831138C59A326C6B4B62A',
    body='''
    <license>
      <signature>hxtHm27FFKUJPsimYmokVVwjyqMrTJFZZxkMvbZ+VCxiqzdZkmAPMUuDNblGQ+MH3+5Y8K3Uc/43yPv2W2Uhbd/8V2uXLXjihHPy6pY1wA/4TdZ5TLmG5ZJr4pI9ixcaHTCgL8Domn7VFjCVvNQU3pFlrVm7LV9SkC2qrPXYsXRP/d6x6neQusYGbajxDH44UIWdFZrrMVAoK06qIjK+R9v9ir5Kkt9LCxzLfAWcV73hady17aNWGc33OCq9lNUUYaSV/yDElPTmrc4pQR0paSbwDdspj9XSC6RHciZPcwq8EMpZyWy3muoDAFAtx8JmyqhufuscTnsD4zSNAtam8w==</signature>
      <payload>
        <type>fixed-sourcetype</type>
        <group_id>Enterprise</group_id>
        <quota>107374182400000</quota>
        <max_violations>5</max_violations>
        <window_period>30</window_period>
        <creation_time>1594969200</creation_time>
        <label>IT Service Intelligence Internals *DO NOT COPY*</label>
        <expiration_time>2163221999</expiration_time>
        <features>
          <feature>Auth</feature>
          <feature>FwdData</feature>
          <feature>LocalSearch</feature>
          <feature>ScheduledSearch</feature>
          <feature>Alerting</feature>
          <feature>SplunkWeb</feature>
        </features>
        <add_ons>
          <add_on name="itsi" type="app">
            <parameter key="size" value="1"/>
          </add_on>
        </add_ons>
        <sourcetypes>
          <sourcetype>itsi_*</sourcetype>
        </sourcetypes>
        <guid>B05DBFD6-D8A0-4DA4-B238-B981EA553954</guid>
      </payload>
    </license>    
    '''
)

license_expiration_signaling_license = License(
    name='Expired license signaling license',
    hash='DC49789D8AAEAC933C29458918661405660AF88A2236B256B9012BE20F10A428',
    body='''
    <license>
      <signature>QBO1jf6NK6L15ZaVbg5fJiBwu5BYms1I1Z6dnIaG5qhKzMT2Ha4eQ9WCb67SfT3LD7RxTfFINGumCVijIzCxMKfYci1YkYmvH9luP0OprnFhiq1vYCC03A7kQb3WG/hgvdJBz9in7+6B2EAL0SwhBtotLzCSXGwufJXCZfKiABDoseETwfzu2QCOF3oYxTSKXaWOZ+4Wl3ExbZkJgCi3++hFyhfaKZmfSNpyoJlhuuBxhmvp6S0C49hrET18UURC9dVrHD8mYI4K1ldAOLs6R1IazoIGcPmFe2HiMaT4Z0ec1u3PXsFUvwTN1WlTTsIPP7ENflzDuAD/Vl2+SCHNQg==</signature>
      <payload>
        <type>fixed-sourcetype</type>
        <group_id>Enterprise</group_id>
        <quota>107374182400000</quota>
        <max_violations>5</max_violations>
        <window_period>30</window_period>
        <creation_time>1594969200</creation_time>
        <label>IT Service Intelligence Internals *DO NOT COPY*</label>
        <expiration_time>2163221999</expiration_time>
        <features>
          <feature>Auth</feature>
          <feature>FwdData</feature>
          <feature>LocalSearch</feature>
          <feature>ScheduledSearch</feature>
          <feature>Alerting</feature>
          <feature>SplunkWeb</feature>
        </features>
        <add_ons>
          <add_on name="itsi" type="app">
            <parameter key="size" value="1"/>
          </add_on>
        </add_ons>
        <sourcetypes>
          <sourcetype>itsi_*</sourcetype>
        </sourcetypes>
        <guid>784417C4-631B-4DE2-80AD-9987859BB023</guid>
      </payload>
    </license>
    '''
)

itsi_internal_license_devtest = License(
    name='ITSI General Sourcetype License DevTest',
    body='''
    <license>
        <signature>uWTD4nZ1NUY5qETP3hbefmq72O050MzGmgx3omhsHqEfyciM6nzL7je+m3WMQOpd0UHl138HXduHcgipmypxeZsLsop0J0Yerfurzw1uyJMGjGVtEfl98Sfil98OAmYzdg7ry17fLJN+WSF8Gl0Zt3kZFdehAoXmfz9i2aA5CwrNr0LxfviWMAd8MTnSCwzsXz6FeNGrYqjjm52F36YqdOA/PL/TraHts2D22CtMWuXSfrGbCHyEEDdEoYKBsRzIGjNC+hjr00msFdWdNUo/285NhQNanK1mCdDJTtcOyS1o7lm+6OqgsgSkcxhMJWq6mLuxkhCz2bWFNQFHs9HHqg==</signature>
        <payload>
            <type>fixed-sourcetype</type>
            <group_id>Enterprise</group_id>
            <quota>107374182400000</quota>
            <max_violations>5</max_violations>
            <window_period>30</window_period>
            <creation_time>1594969200</creation_time>
            <label>IT Service Intelligence Internals *DO NOT COPY*</label>
            <expiration_time>2163221999</expiration_time>
            <subgroup_id>DevTest</subgroup_id>
            <features>
                <feature>Auth</feature>
                <feature>FwdData</feature>
                <feature>LocalSearch</feature>
                <feature>ScheduledSearch</feature>
                <feature>Alerting</feature>
                <feature>SplunkWeb</feature>
            </features>
            <add_ons>
                <add_on name="itsi" type="app">
                    <parameter key="size" value="1"/>
                </add_on>
            </add_ons>
            <sourcetypes>
                <sourcetype>itsi_*</sourcetype>
            </sourcetypes>
            <guid>D3C8E133-5424-4127-8156-AD3623789BB0</guid>
        </payload>
    </license>    
    '''
)

plus_suite_signaling_license_devtest = License(
    name='ITSI Plus suite signaling license DevTest',
    hash='FB79890C9C2463A31A620E3329A302BE264C8418B0681C9DE403E919F7D598A9',
    body='''
    <license>
        <signature>afW2VCjdEyNTl7l9dvYo5aPS4NeLa7atqCPckZBXlQARdsR1ROoXWgyVCk1i1LqNTfAxQSPyvDMVwKoGfG5yIYu247+XzaAgguHJfe4k/g/sgm4qJhGnMJdQfLoMkWyDh2MvocOCvPMP4bzUzG3w8DOewEX42rDZ77VHhKmEhUaJCbQxoEgaJF12XMmF7cYB+Wefqk/5LCa+TPCYkTBZ5q0oVYeslQbiEGlC4N1YrxIXNeOv0SawLY9kSICrZEWKy9A8goRUjHrOdQHrbt+rTxUo5G2TAjsWe0y2Q2txFbRseTplt2ToKQCNk2mrjm9D71KrHq52dVzCTut3zol/2A==</signature>
        <payload>
            <type>fixed-sourcetype</type>
            <group_id>Enterprise</group_id>
            <quota>107374182400000</quota>
            <max_violations>5</max_violations>
            <window_period>30</window_period>
            <creation_time>1594969200</creation_time>
            <label>IT Service Intelligence Internals *DO NOT COPY*</label>
            <expiration_time>2163221999</expiration_time>
            <subgroup_id>DevTest</subgroup_id>
            <features>
                <feature>Auth</feature>
                <feature>FwdData</feature>
                <feature>LocalSearch</feature>
                <feature>ScheduledSearch</feature>
                <feature>Alerting</feature>
                <feature>SplunkWeb</feature>
            </features>
            <add_ons>
                <add_on name="itsi" type="app">
                    <parameter key="size" value="1"/>
                </add_on>
            </add_ons>
            <sourcetypes>
                <sourcetype>itsi_*</sourcetype>
            </sourcetypes>
            <guid>6B95FFBB-EBB4-4A1C-9EFC-B483487875F9</guid>
        </payload>
    </license>
    '''
)

license_expiration_signaling_license_devtest = License(
    name='Expired license signaling license DevTest',
    hash='247B4903C2EECFC2AE04A93EAD2085BB183AED6BFF851E4B72D0C38959A81252',
    body='''
    <license>
        <signature>MvS7xJZAB75MMUsDSig6vvu2V3PBZOCsDkz+K41PcqBDgw/cJ4SJXOu/EdzEzIbymF1Rgw1CiOnMqarP/1j+WZbYiCd90/DzsJnNcrixHXNEVUc+pib1uTPjAhCpq4xI4HPznwZyWo0OsOxDxIbmGqhlUy7kNhD7/EGljC7WzVTqpgrNs0PIkcJyCBg7lxFqMn6NuG/zRHLi4jzxGTrkwAcg57vGje/AiR0lEjiKai6IAF4uMr2erJTBN0fpvJbQsElE2DorUhtRMZtZ99kSkxnOmQdmKasaeJKW9lBWRrBsVfCKXOQ5s3MfoK40JawlMde5sZToRR9UzaKlgbB5uw==</signature>
        <payload>
            <type>fixed-sourcetype</type>
            <group_id>Enterprise</group_id>
            <quota>107374182400000</quota>
            <max_violations>5</max_violations>
            <window_period>30</window_period>
            <creation_time>1594969200</creation_time>
            <label>IT Service Intelligence Internals *DO NOT COPY*</label>
            <expiration_time>2163221999</expiration_time>
            <subgroup_id>DevTest</subgroup_id>
            <features>
                <feature>Auth</feature>
                <feature>FwdData</feature>
                <feature>LocalSearch</feature>
                <feature>ScheduledSearch</feature>
                <feature>Alerting</feature>
                <feature>SplunkWeb</feature>
            </features>
            <add_ons>
                <add_on name="itsi" type="app">
                    <parameter key="size" value="1"/>
                </add_on>
            </add_ons>
            <sourcetypes>
                <sourcetype>itsi_*</sourcetype>
            </sourcetypes>
            <guid>E6CF109F-E521-4D07-BEC3-99329B3FD047</guid>
        </payload>
    </license>
    '''
)

new_itsi_internal_licenses = [
    itsi_internal_license,
    plus_suite_signaling_license,
    license_expiration_signaling_license]
new_itsi_internal_licenses_dev_test = [
    itsi_internal_license_devtest,
    plus_suite_signaling_license_devtest,
    license_expiration_signaling_license_devtest]
old_itsi_internal_ea_licenses = [old_itsi_internal_ea_license]
all_itsi_internal_licenses = old_itsi_internal_ea_licenses + \
                             new_itsi_internal_licenses + \
                             new_itsi_internal_licenses_dev_test
itsi_internal_licenses = new_itsi_internal_licenses + [old_itsi_internal_ea_licenses]
itsi_internal_licenses_dev_test = new_itsi_internal_licenses_dev_test + [old_itsi_internal_ea_license]


def verify_licenses(licenses):
    license_guids = {lic.guid for lic in licenses}
    assert len(license_guids) == len(licenses), 'Internal licences have duplicate GUIDs'

    license_hashes = [lic.hash for lic in licenses if lic.hash is not None]
    assert len(license_hashes) == len(set(license_hashes)), 'Internal licences have duplicate hashes'


verify_licenses(all_itsi_internal_licenses)

# flake8: noqa
