# Metadefender

Publisher: Splunk \
Connector Version: 2.0.8 \
Product Vendor: OPSWAT \
Product Name: Metadefender \
Minimum Product Version: 5.1.0

This app connects to OPSWAT Metadefender for performing investigative actions pertaining to reputation checking for ip and file

### Configuration variables

This table lists the configuration variables required to operate Metadefender. These variables are specified when configuring a Metadefender asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_key** | required | password | API key |

### Supported Actions

[ip reputation](#action-ip-reputation) - Gets information about an IP \
[file reputation](#action-file-reputation) - Gets information about a hash \
[test connectivity](#action-test-connectivity) - Validates the asset configuration for connectivity

## action: 'ip reputation'

Gets information about an IP

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP address to query | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 0.0.0.0 8.8.8.8 |
action_result.data.\*.address | string | | 1.1.1.1 |
action_result.data.\*.geo_info.city.code | string | | |
action_result.data.\*.geo_info.city.name | string | | Tempe |
action_result.data.\*.geo_info.continent.code | string | | NA |
action_result.data.\*.geo_info.continent.name | string | | North America |
action_result.data.\*.geo_info.country.code | string | | US |
action_result.data.\*.geo_info.country.name | string | | United States |
action_result.data.\*.geo_info.location.latitude | numeric | | 51.4964 |
action_result.data.\*.geo_info.location.longitude | numeric | | -0.1224 |
action_result.data.\*.geo_info.registered_country.code | string | | US |
action_result.data.\*.geo_info.registered_country.name | string | | United States |
action_result.data.\*.geo_info.subdivisions.\*.code | string | | AZ |
action_result.data.\*.geo_info.subdivisions.\*.name | string | | Arizona |
action_result.data.\*.lookup_results.address | string | `ip` | 109.229.210.250 |
action_result.data.\*.lookup_results.detected_by | numeric | | 0 1 |
action_result.data.\*.lookup_results.sources.\*.assessment | string | | botnet, zeus |
action_result.data.\*.lookup_results.sources.\*.detect_time | string | | 2019-02-20T11:39:49.612487Z |
action_result.data.\*.lookup_results.sources.\*.provider | string | | spamhaus.org |
action_result.data.\*.lookup_results.sources.\*.status | numeric | | 0 |
action_result.data.\*.lookup_results.sources.\*.update_time | string | | 2019-02-20T11:39:49.764370 |
action_result.data.\*.lookup_results.start_time | string | | 2019-02-28T11:59:13.989Z |
action_result.summary.detected_by | numeric | | 0 1 |
action_result.message | string | | Detected by: 0 Detected by: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'file reputation'

Gets information about a hash

Type: **investigate** \
Read only: **True**

If additional_info is checked, additional_details will be populated with available data.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash (md5, sha1, sha256) | string | `hash` `md5` `sha1` `sha256` |
**additional_info** | optional | Fetch additional information about the file if available | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_info | boolean | | False True |
action_result.parameter.hash | string | `hash` `md5` `sha1` `sha256` | 77AB8B360C0D5BB07E61D91D7A114A813797DFA0328B90A010DFCC30CE465679 |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.autoRemoveFromRecents | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.configChanges | numeric | | 1152 |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.excludeFromRecents | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.exported | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.finishOnTaskLaunch | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.hardwareAccelerated | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.icon | string | | resourceId:0x7f070116 |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.intentFilters.\*.actions.\*.name | string | | android.intent.action.MAIN |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.intentFilters.\*.categories.\*.name | string | | android.intent.category.LAUNCHER |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.intentFilters.\*.data.\*.scheme | string | | tagmanager.c.com.jadev.icerunner |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.label | string | | Download Manager |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.launchMode | numeric | | 1 |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.multiprocess | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.name | string | | com.tool.downldmngr.downloadmanager.StartActivity |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.noHistory | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.resizeableActivity | boolean | | False |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.screenOrientation | numeric | | -1 |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.taskAffinity | string | | com.cmcm.adsdk.nativead |
action_result.data.\*.additional_details.apk-manifest.application.activities.\*.theme | string | | resourceId:0x7f1000a6 |
action_result.data.\*.additional_details.apk-manifest.application.allowBackup | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.hardwareAccelerated | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.icon | string | | resourceId:0x7f070182 |
action_result.data.\*.additional_details.apk-manifest.application.label | string | | resourceId:0x7f0f0028 |
action_result.data.\*.additional_details.apk-manifest.application.largeHeap | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.launcherActivities.\*.excludeFromRecents | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.launcherActivities.\*.icon | string | | resourceId:0x7f070116 |
action_result.data.\*.additional_details.apk-manifest.application.launcherActivities.\*.intentFilters.\*.actions.\*.name | string | | android.intent.action.MAIN |
action_result.data.\*.additional_details.apk-manifest.application.launcherActivities.\*.intentFilters.\*.categories.\*.name | string | | android.intent.category.LAUNCHER |
action_result.data.\*.additional_details.apk-manifest.application.launcherActivities.\*.label | string | | Download Manager |
action_result.data.\*.additional_details.apk-manifest.application.launcherActivities.\*.name | string | | com.tool.downldmngr.downloadmanager.StartActivity |
action_result.data.\*.additional_details.apk-manifest.application.launcherActivities.\*.noHistory | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.launcherActivities.\*.theme | string | | resourceId:0x7f1000a6 |
action_result.data.\*.additional_details.apk-manifest.application.name | string | | com.tool.downldmngr.downloadmanager.MyApp |
action_result.data.\*.additional_details.apk-manifest.application.providers.\*.authorities | string | | com.jadev.icerunner.firebaseinitprovider |
action_result.data.\*.additional_details.apk-manifest.application.providers.\*.exported | boolean | | False |
action_result.data.\*.additional_details.apk-manifest.application.providers.\*.initOrder | numeric | | 100 |
action_result.data.\*.additional_details.apk-manifest.application.providers.\*.name | string | | com.google.firebase.provider.FirebaseInitProvider |
action_result.data.\*.additional_details.apk-manifest.application.receivers.\*.enabled | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.receivers.\*.exported | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.receivers.\*.intentFilters.\*.actions.\*.name | string | | android.provider.Telephony.SMS_RECEIVED |
action_result.data.\*.additional_details.apk-manifest.application.receivers.\*.intentFilters.\*.categories.\*.name | string | | android.intent.category.HOME |
action_result.data.\*.additional_details.apk-manifest.application.receivers.\*.intentFilters.\*.data.\*.scheme | string | | package |
action_result.data.\*.additional_details.apk-manifest.application.receivers.\*.label | string | | Extend your battery life |
action_result.data.\*.additional_details.apk-manifest.application.receivers.\*.metaData.\*.name | string | | android.app.device_admin |
action_result.data.\*.additional_details.apk-manifest.application.receivers.\*.metaData.\*.resource | string | | resourceId:0x7f120001 |
action_result.data.\*.additional_details.apk-manifest.application.receivers.\*.name | string | | com.mobcore.m2dev.sms.MySmsReceiver |
action_result.data.\*.additional_details.apk-manifest.application.receivers.\*.permission | string | | android.permission.BIND_DEVICE_ADMIN |
action_result.data.\*.additional_details.apk-manifest.application.receivers.\*.process | string | | |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.enabled | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.exported | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.intentFilters.\*.actions.\*.name | string | | com.yandex.metrica.IMetricaService |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.intentFilters.\*.categories.\*.name | string | | android.intent.category.DEFAULT |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.intentFilters.\*.data.\*.scheme | string | | metrica |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.intentFilters.\*.priority | numeric | | -500 |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.label | string | | OUR accessibility service! |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.launchMode | numeric | | 1 |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.metaData.\*.name | string | | metrica:api:level |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.metaData.\*.resource | string | | resourceId:0x7f120000 |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.metaData.\*.value | numeric | | 52 |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.multiprocess | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.name | string | | com.mobcore.m2dev.bgload.BackgroundLoaderService |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.permission | string | | android.permission.BIND_ACCESSIBILITY_SERVICE |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.persistent | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.services.\*.process | string | | :Metrica |
action_result.data.\*.additional_details.apk-manifest.application.supportsRtl | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.application.theme | string | | resourceId:0x7f100006 |
action_result.data.\*.additional_details.apk-manifest.application.usesLibraries.\*.name | string | | org.apache.http.legacy |
action_result.data.\*.additional_details.apk-manifest.application.usesLibraries.\*.required | boolean | | False |
action_result.data.\*.additional_details.apk-manifest.installLocation | numeric | | 1 |
action_result.data.\*.additional_details.apk-manifest.instrumentation | string | | |
action_result.data.\*.additional_details.apk-manifest.package | string | | com.jadev.icerunner |
action_result.data.\*.additional_details.apk-manifest.permissions.\*.name | string | | ACTION_USAGE_ACCESS_SETTINGS |
action_result.data.\*.additional_details.apk-manifest.permissions.\*.protectionLevel | numeric | | 2 |
action_result.data.\*.additional_details.apk-manifest.platformBuildVersionCode | numeric | | 1 |
action_result.data.\*.additional_details.apk-manifest.platformBuildVersionName | numeric | | 1084479242 |
action_result.data.\*.additional_details.apk-manifest.supportsScreens.anyDensity | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.supportsScreens.largeScreens | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.supportsScreens.normalScreens | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.supportsScreens.resizeable | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.supportsScreens.smallScreens | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.supportsScreens.xlargeScreens | boolean | | True |
action_result.data.\*.additional_details.apk-manifest.usesConfiguration | string | | |
action_result.data.\*.additional_details.apk-manifest.usesFeatures.\*.glEsVersion | numeric | | 131072 |
action_result.data.\*.additional_details.apk-manifest.usesFeatures.\*.name | string | | android.hardware.telephony |
action_result.data.\*.additional_details.apk-manifest.usesFeatures.\*.required | boolean | | False |
action_result.data.\*.additional_details.apk-manifest.usesPermissions.\*.maxSdkVersion | numeric | | 28 |
action_result.data.\*.additional_details.apk-manifest.usesPermissions.\*.name | string | | android.permission.PACKAGE_USAGE_STATS |
action_result.data.\*.additional_details.apk-manifest.usesSdk.minSdkVersion | numeric | | 19 |
action_result.data.\*.additional_details.apk-manifest.usesSdk.targetSdkVersion | numeric | | 27 |
action_result.data.\*.additional_details.apk-manifest.versionCode | numeric | | 1 |
action_result.data.\*.additional_details.apk-manifest.versionName | string | | 5.12 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.categories.\*.category_name | string | | Unclassified |
action_result.data.\*.additional_details.appinfo.appinfo.\*.categories.\*.wa_category_id | string | | 10 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.computer_type_stats.\*.computer_type | string | | laptop |
action_result.data.\*.additional_details.appinfo.appinfo.\*.computer_type_stats.\*.computer_type_count | numeric | | 77 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.computer_type_stats.\*.computer_type_rank_over_sha1 | numeric | | 0 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.device_identity_stats.\*.device_identity_count | numeric | | 1 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.device_identity_stats.\*.device_identity_count_rank_over_sha1 | numeric | | 0 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.device_identity_stats.\*.reported_ts_yyww | string | | 1739 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.file_infos.\*.file_name | string | | KMService.exe |
action_result.data.\*.additional_details.appinfo.appinfo.\*.file_infos.\*.file_name_lower | string | | kmservice.exe |
action_result.data.\*.additional_details.appinfo.appinfo.\*.file_infos.\*.file_property_version | string | | |
action_result.data.\*.additional_details.appinfo.appinfo.\*.file_infos.\*.file_property_version_norm | string | | |
action_result.data.\*.additional_details.appinfo.appinfo.\*.file_infos.\*.file_size | numeric | | 0 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.file_infos.\*.sha1 | string | | 01C7D28E8828A91C27FFE0F1155CFA835FA6D703 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.file_path_stats.\*.file_path | string | | \\windows\\kmservice.exe |
action_result.data.\*.additional_details.appinfo.appinfo.\*.file_path_stats.\*.file_path_count | numeric | | 710 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.file_path_stats.\*.file_path_rank_over_sha1 | numeric | | 0 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.loaded_component_stats.\*.loaded_component | string | | 0119C23D88292A0E4FEC04D5CF8629005A44E37C |
action_result.data.\*.additional_details.appinfo.appinfo.\*.loaded_component_stats.\*.loaded_component_count | numeric | | 172 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.os_infos.\*.arch | string | | 64-bit |
action_result.data.\*.additional_details.appinfo.appinfo.\*.os_infos.\*.kernel_version | string | | 6.1.7600 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.os_infos.\*.language | string | | |
action_result.data.\*.additional_details.appinfo.appinfo.\*.os_infos.\*.os_name | string | | Microsoft Windows 7 Ultimate |
action_result.data.\*.additional_details.appinfo.appinfo.\*.os_infos.\*.os_name_norm | string | | microsoft windows 7 ultimate |
action_result.data.\*.additional_details.appinfo.appinfo.\*.os_infos.\*.os_type | numeric | | 1 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.os_infos.\*.service_pack | string | | |
action_result.data.\*.additional_details.appinfo.appinfo.\*.os_infos.\*.wa_os_id | string | | 34 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.product_info_stats.\*.product_name_norm | string | | wordpad |
action_result.data.\*.additional_details.appinfo.appinfo.\*.product_info_stats.\*.product_name_norm_count | numeric | | 715 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.product_info_stats.\*.product_name_norm_rank_over_sha1 | numeric | | 0 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.product_info_stats.\*.product_version_norm | string | | 6 1 7600 16385 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.product_infos.\*.product_name | string | | WordPad |
action_result.data.\*.additional_details.appinfo.appinfo.\*.product_infos.\*.product_version | string | | 6.1.7600.16385 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.product_infos.\*.wa_product_id | string | | 2875 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.product_infos.\*.wa_signature_id | string | | 2925 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.source_ip_stats.\*.reported_ts_yyww | string | | 1739 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.source_ip_stats.\*.source_ip_count | numeric | | 1 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.source_ip_stats.\*.source_ip_count_rank_over_sha1 | numeric | | 0 |
action_result.data.\*.additional_details.appinfo.appinfo.\*.vendor_infos.\*.vendor_name | string | | Microsoft Corporation |
action_result.data.\*.additional_details.appinfo.appinfo.\*.vendor_infos.\*.wa_vendor_id | string | | 90 |
action_result.data.\*.additional_details.appinfo.source | string | | metascan |
action_result.data.\*.additional_details.exif.BitDepth | numeric | | 8 |
action_result.data.\*.additional_details.exif.ColorType | string | | RGB |
action_result.data.\*.additional_details.exif.Compression | string | | Deflate/Inflate |
action_result.data.\*.additional_details.exif.FileSize | string | | 162 kB |
action_result.data.\*.additional_details.exif.FileType | string | | PNG |
action_result.data.\*.additional_details.exif.FileTypeExtension | string | | png |
action_result.data.\*.additional_details.exif.Filter | string | | Adaptive |
action_result.data.\*.additional_details.exif.Gamma | numeric | | 2.2 |
action_result.data.\*.additional_details.exif.ImageHeight | numeric | | 1080 |
action_result.data.\*.additional_details.exif.ImageSize | string | | 1920x1080 |
action_result.data.\*.additional_details.exif.ImageWidth | numeric | | 1920 |
action_result.data.\*.additional_details.exif.Interlace | string | | Noninterlaced |
action_result.data.\*.additional_details.exif.MIMEType | string | | image/png |
action_result.data.\*.additional_details.exif.Megapixels | numeric | | 2.1 |
action_result.data.\*.additional_details.exif.PixelUnits | string | | meters |
action_result.data.\*.additional_details.exif.PixelsPerUnitX | numeric | | 4724 |
action_result.data.\*.additional_details.exif.PixelsPerUnitY | numeric | | 4724 |
action_result.data.\*.additional_details.exif.SRGBRendering | string | | Perceptual |
action_result.data.\*.additional_details.peinfo.headers.compilation_time | string | | 01/28/2010 06:26:44 |
action_result.data.\*.additional_details.peinfo.headers.machine_type | string | | IMAGE_FILE_MACHINE_I386 |
action_result.data.\*.additional_details.peinfo.headers.number_of_sections | numeric | | 3 |
action_result.data.\*.additional_details.peinfo.headers.number_of_symbols | numeric | | 0 |
action_result.data.\*.additional_details.peinfo.headers.optional_header_size | numeric | | 224 |
action_result.data.\*.additional_details.peinfo.headers.pointer_to_symbol_table | string | | 0 |
action_result.data.\*.additional_details.peinfo.imphash | string | | dd153b71f091fb527f30c9812532fb6f |
action_result.data.\*.additional_details.peinfo.imported_dlls.\*.name | string | | KERNEL32.DLL |
action_result.data.\*.additional_details.peinfo.optional_headers.checksum | string | | 0 |
action_result.data.\*.additional_details.peinfo.optional_headers.code_size | numeric | | 98304 |
action_result.data.\*.additional_details.peinfo.optional_headers.entry_point | string | | 0xeab0 |
action_result.data.\*.additional_details.peinfo.optional_headers.image_size | numeric | | 155648 |
action_result.data.\*.additional_details.peinfo.optional_headers.image_version | string | | 0.0 |
action_result.data.\*.additional_details.peinfo.optional_headers.initialized_data_size | numeric | | 53248 |
action_result.data.\*.additional_details.peinfo.optional_headers.linker_version | string | | 6.0 |
action_result.data.\*.additional_details.peinfo.optional_headers.os_version | string | | 4.0 |
action_result.data.\*.additional_details.peinfo.optional_headers.pe_type | string | | 0x10b |
action_result.data.\*.additional_details.peinfo.optional_headers.subsystem | string | | IMAGE_SUBSYSTEM_WINDOWS_CUI |
action_result.data.\*.additional_details.peinfo.optional_headers.subsystem_version | string | | 4.0 |
action_result.data.\*.additional_details.peinfo.optional_headers.uninitialized_data_size | numeric | | 0 |
action_result.data.\*.additional_details.peinfo.pehash | string | | 1d49470924fc06bd8cc0c07c917738b86062832f |
action_result.data.\*.additional_details.peinfo.section_headers.\*.entropy | numeric | | 6.16855808513436 |
action_result.data.\*.additional_details.peinfo.section_headers.\*.md5 | string | | 847c8f3c2c65367d9bc7a421249dcdec |
action_result.data.\*.additional_details.peinfo.section_headers.\*.name | string | | .text |
action_result.data.\*.additional_details.peinfo.section_headers.\*.number_of_linenumbers | numeric | | 0 |
action_result.data.\*.additional_details.peinfo.section_headers.\*.number_of_relocations | numeric | | 0 |
action_result.data.\*.additional_details.peinfo.section_headers.\*.pointer_to_linenumbers | string | | 0x0 |
action_result.data.\*.additional_details.peinfo.section_headers.\*.pointer_to_raw_data | string | | 0x1000 |
action_result.data.\*.additional_details.peinfo.section_headers.\*.pointer_to_relocations | string | | 0x0 |
action_result.data.\*.additional_details.peinfo.section_headers.\*.raw_size | numeric | | 98304 |
action_result.data.\*.additional_details.peinfo.section_headers.\*.virtual_address | string | | 0x1000 |
action_result.data.\*.additional_details.peinfo.section_headers.\*.virtual_size | numeric | | 95770 |
action_result.data.\*.additional_details.peinfo.signature.parsing_error | string | | The PE file does not contain a certificate table. |
action_result.data.\*.appinfo | boolean | | True False |
action_result.data.\*.data_id | string | | ZDE4MDgyM3JKNFhmY3EyTFhya3I3R3FxaDht |
action_result.data.\*.extracted_files.data_id | string | | bzE5MDIxOEJ5emdqTGFfckVCeVhBZEVpbkFO |
action_result.data.\*.extracted_files.files_in_archive.\*.data_id | string | | YnpFNU1ESXhPRUo1ZW1kcVRHRmZja1Vya0FlSFlXbjZDNA |
action_result.data.\*.extracted_files.files_in_archive.\*.detected_by | numeric | | 1 |
action_result.data.\*.extracted_files.files_in_archive.\*.display_name | string | | resources.arsc |
action_result.data.\*.extracted_files.files_in_archive.\*.file_size | numeric | | 945780 |
action_result.data.\*.extracted_files.files_in_archive.\*.file_type | string | | application/octet-stream |
action_result.data.\*.extracted_files.files_in_archive.\*.progress_percentage | numeric | | 100 |
action_result.data.\*.extracted_files.files_in_archive.\*.scan_result_i | numeric | | 1 |
action_result.data.\*.file_id | string | | ZDE4MDgyM3JKNFhmY3EyTFg |
action_result.data.\*.file_info.display_name | string | | test.doc |
action_result.data.\*.file_info.file_size | numeric | | 22528 |
action_result.data.\*.file_info.file_type_category | string | | D |
action_result.data.\*.file_info.file_type_description | string | | Microsoft Word Document |
action_result.data.\*.file_info.file_type_extension | string | | docx |
action_result.data.\*.file_info.md5 | string | `hash` `md5` | F8B03C9F5E359AA0620859CA42E59CCE |
action_result.data.\*.file_info.sha1 | string | `hash` `sha1` | C46143B392F8A5B2F5B3A537C8FFF2E181DB1815 |
action_result.data.\*.file_info.sha256 | string | `hash` `sha256` | 77AB8B360C0D5BB07E61D91D7A114A813797DFA0328B90A010DFCC30CE465679 |
action_result.data.\*.file_info.upload_timestamp | string | | 2018-08-23T20:33:15.342Z |
action_result.data.\*.malware_family | string | | android |
action_result.data.\*.parent_data_id | string | | |
action_result.data.\*.process_info.blocked_reason | string | | Infected |
action_result.data.\*.process_info.file_type_skipped_scan | boolean | | True False |
action_result.data.\*.process_info.post_processing.actions_failed | string | | |
action_result.data.\*.process_info.post_processing.actions_ran | string | | Sanitized |
action_result.data.\*.process_info.post_processing.converted_destination | string | | description_sanitized_by_OPSWAT_MetaDefender_f311f39ac4b5453093aa8fdd6fec1480.png |
action_result.data.\*.process_info.post_processing.converted_to | string | | png |
action_result.data.\*.process_info.post_processing.copy_move_destination | string | | |
action_result.data.\*.process_info.profile | string | | File scan |
action_result.data.\*.process_info.progress_percentage | numeric | | 100 |
action_result.data.\*.process_info.result | string | | Allowed |
action_result.data.\*.process_info.user_agent | string | | MDClient |
action_result.data.\*.rest_version | string | | 4 |
action_result.data.\*.sandbox | boolean | | True False |
action_result.data.\*.sanitized.data_id | string | | ZzE4MTIwN1NrRC1HTGpnT0pOLnNhbml0aXplZHIxSExqZWQxNA |
action_result.data.\*.sanitized.reason | string | | |
action_result.data.\*.sanitized.result | string | | Allowed |
action_result.data.\*.scan_result_history_length | numeric | | 1 |
action_result.data.\*.scan_results.data_id | string | | ZDE4MDgyM3JKNFhmY3EyTFhya3I3R3FxaDht |
action_result.data.\*.scan_results.progress_percentage | numeric | | 100 |
action_result.data.\*.scan_results.rescan_available | boolean | | False True |
action_result.data.\*.scan_results.scan_all_result_a | string | | No Threat Detected |
action_result.data.\*.scan_results.scan_all_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.\*.def_time | string | | |
action_result.data.\*.scan_results.scan_details.\*.scan_result_i | numeric | | |
action_result.data.\*.scan_results.scan_details.\*.scan_time | numeric | | |
action_result.data.\*.scan_results.scan_details.\*.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.AVG.def_time | string | | 2015-05-17T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.AVG.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.AVG.scan_time | numeric | | 78 |
action_result.data.\*.scan_results.scan_details.AVG.threat_found | string | | Win32/Parite |
action_result.data.\*.scan_results.scan_details.AegisLab.def_time | string | | 2018-12-06T01:00:00.000Z |
action_result.data.\*.scan_results.scan_details.AegisLab.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.AegisLab.scan_time | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.AegisLab.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Agnitum.def_time | string | | 2018-12-01T12:59:00.000Z |
action_result.data.\*.scan_results.scan_details.Agnitum.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Agnitum.scan_time | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.Agnitum.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Ahnlab.def_time | string | | 2018-12-07T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Ahnlab.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Ahnlab.scan_time | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Ahnlab.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Antiy.def_time | string | | 2018-12-07T07:46:00.000Z |
action_result.data.\*.scan_results.scan_details.Antiy.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Antiy.scan_time | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.Antiy.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Avira.def_time | string | | 2018-12-05T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Avira.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Avira.scan_time | numeric | | 8 |
action_result.data.\*.scan_results.scan_details.Avira.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Baidu.def_time | string | | 2015-05-18T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Baidu.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.Baidu.scan_time | numeric | | 9500 |
action_result.data.\*.scan_results.scan_details.Baidu.threat_found | string | | Virus.Win32.Parite.$b |
action_result.data.\*.scan_results.scan_details.BitDefender.def_time | string | | 2018-12-07T06:13:00.000Z |
action_result.data.\*.scan_results.scan_details.BitDefender.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.BitDefender.scan_time | numeric | | 13 |
action_result.data.\*.scan_results.scan_details.BitDefender.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.ByteHero.def_time | string | | 2018-12-06T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.ByteHero.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.ByteHero.scan_time | numeric | | 194 |
action_result.data.\*.scan_results.scan_details.ByteHero.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.ClamAV.def_time | string | | 2018-12-07T02:22:00.000Z |
action_result.data.\*.scan_results.scan_details.ClamAV.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.ClamAV.scan_time | numeric | | 33 |
action_result.data.\*.scan_results.scan_details.ClamAV.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.ClamWin.def_time | string | | 2015-05-18T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.ClamWin.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.ClamWin.scan_time | numeric | | 188 |
action_result.data.\*.scan_results.scan_details.ClamWin.threat_found | string | | Heuristics.W32.Parite.B |
action_result.data.\*.scan_results.scan_details.Comodo.def_time | string | | 2021-01-29T05:05:50.000Z |
action_result.data.\*.scan_results.scan_details.Comodo.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.Comodo.scan_time | numeric | | 6209 |
action_result.data.\*.scan_results.scan_details.Comodo.threat_found | string | | Application.Win32.HackTool.HackKMS.EB |
action_result.data.\*.scan_results.scan_details.CrowdStrike Falcon ML.def_time | string | | 2021-01-29T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.CrowdStrike Falcon ML.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.CrowdStrike Falcon ML.scan_time | numeric | | 2462 |
action_result.data.\*.scan_results.scan_details.CrowdStrike Falcon ML.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Cyren.def_time | string | | 2018-12-07T12:15:00.000Z |
action_result.data.\*.scan_results.scan_details.Cyren.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Cyren.scan_time | numeric | | 12 |
action_result.data.\*.scan_results.scan_details.Cyren.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Dr.Web Gateway.def_time | string | | 2015-05-18T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Dr.Web Gateway.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.Dr.Web Gateway.scan_time | numeric | | 265 |
action_result.data.\*.scan_results.scan_details.Dr.Web Gateway.threat_found | string | | Win32.Parite.2 |
action_result.data.\*.scan_results.scan_details.ESET.def_time | string | | 2018-12-07T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.ESET.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.ESET.scan_time | numeric | | 5 |
action_result.data.\*.scan_results.scan_details.ESET.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Emsisoft.def_time | string | | 2018-12-07T03:50:00.000Z |
action_result.data.\*.scan_results.scan_details.Emsisoft.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Emsisoft.scan_time | numeric | | 7 |
action_result.data.\*.scan_results.scan_details.Emsisoft.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.F-prot.def_time | string | | 2018-12-07T08:37:00.000Z |
action_result.data.\*.scan_results.scan_details.F-prot.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.F-prot.scan_time | numeric | | 2 |
action_result.data.\*.scan_results.scan_details.F-prot.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.F-secure.def_time | string | | 2018-12-06T00:12:00.000Z |
action_result.data.\*.scan_results.scan_details.F-secure.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.F-secure.scan_time | numeric | | 529 |
action_result.data.\*.scan_results.scan_details.F-secure.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Filseclab.def_time | string | | 2018-12-06T00:34:00.000Z |
action_result.data.\*.scan_results.scan_details.Filseclab.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Filseclab.scan_time | numeric | | 170 |
action_result.data.\*.scan_results.scan_details.Filseclab.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Fortinet.def_time | string | | 2018-12-06T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Fortinet.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Fortinet.scan_time | numeric | | 19 |
action_result.data.\*.scan_results.scan_details.Fortinet.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.GFI.def_time | string | | 2015-05-18T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.GFI.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.GFI.scan_time | numeric | | 343 |
action_result.data.\*.scan_results.scan_details.GFI.threat_found | string | | Win32.Parite.b (v) |
action_result.data.\*.scan_results.scan_details.Hauri.def_time | string | | 2018-12-07T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Hauri.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Hauri.scan_time | numeric | | 2 |
action_result.data.\*.scan_results.scan_details.Hauri.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Huorong.def_time | string | | 2018-12-05T09:49:00.000Z |
action_result.data.\*.scan_results.scan_details.Huorong.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Huorong.scan_time | numeric | | 10 |
action_result.data.\*.scan_results.scan_details.Huorong.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Ikarus.def_time | string | | 2018-12-07T13:10:34.000Z |
action_result.data.\*.scan_results.scan_details.Ikarus.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Ikarus.scan_time | numeric | | 15 |
action_result.data.\*.scan_results.scan_details.Ikarus.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Jiangmin.def_time | string | | 2015-05-18T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Jiangmin.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.Jiangmin.scan_time | numeric | | 17332 |
action_result.data.\*.scan_results.scan_details.Jiangmin.threat_found | string | | Win32/Parite.b |
action_result.data.\*.scan_results.scan_details.K7.def_time | string | | 2018-12-07T08:44:00.000Z |
action_result.data.\*.scan_results.scan_details.K7.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.K7.scan_time | numeric | | 3 |
action_result.data.\*.scan_results.scan_details.K7.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Kaspersky.def_time | string | | 2015-05-17T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Kaspersky.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.Kaspersky.scan_time | numeric | | 78 |
action_result.data.\*.scan_results.scan_details.Kaspersky.threat_found | string | | Virus.Win32.Parite.b |
action_result.data.\*.scan_results.scan_details.Lavasoft.def_time | string | | 2015-05-18T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Lavasoft.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.Lavasoft.scan_time | numeric | | 8986 |
action_result.data.\*.scan_results.scan_details.Lavasoft.threat_found | string | | Win32.Parite.B |
action_result.data.\*.scan_results.scan_details.McAfee-Gateway.def_time | string | | 2015-05-18T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.McAfee-Gateway.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.McAfee-Gateway.scan_time | numeric | | 250 |
action_result.data.\*.scan_results.scan_details.McAfee-Gateway.threat_found | string | | W32/Pate.b |
action_result.data.\*.scan_results.scan_details.McAfee.def_time | string | | 2018-12-07T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.McAfee.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.McAfee.scan_time | numeric | | 8 |
action_result.data.\*.scan_results.scan_details.McAfee.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Microsoft Security Essentials.def_time | string | | 2015-05-17T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Microsoft Security Essentials.scan_result_i | numeric | | 10 |
action_result.data.\*.scan_results.scan_details.Microsoft Security Essentials.scan_time | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Microsoft Security Essentials.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.NANOAV.def_time | string | | 2018-12-07T03:32:00.000Z |
action_result.data.\*.scan_results.scan_details.NANOAV.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.NANOAV.scan_time | numeric | | 11 |
action_result.data.\*.scan_results.scan_details.NANOAV.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Preventon.def_time | string | | 2018-12-07T06:01:00.000Z |
action_result.data.\*.scan_results.scan_details.Preventon.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Preventon.scan_time | numeric | | 44 |
action_result.data.\*.scan_results.scan_details.Preventon.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Quick Heal.def_time | string | | 2018-12-06T13:58:00.000Z |
action_result.data.\*.scan_results.scan_details.Quick Heal.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Quick Heal.scan_time | numeric | | 9 |
action_result.data.\*.scan_results.scan_details.Quick Heal.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.RocketCyber.def_time | string | | 2021-01-29T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.RocketCyber.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.RocketCyber.scan_time | numeric | | 14 |
action_result.data.\*.scan_results.scan_details.RocketCyber.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.STOPzilla.def_time | string | | 2015-05-15T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.STOPzilla.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.STOPzilla.scan_time | numeric | | 9578 |
action_result.data.\*.scan_results.scan_details.STOPzilla.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.SUPERAntiSpyware.def_time | string | | 2013-05-22T22:16:00.000Z |
action_result.data.\*.scan_results.scan_details.SUPERAntiSpyware.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.SUPERAntiSpyware.scan_time | numeric | | 848 |
action_result.data.\*.scan_results.scan_details.SUPERAntiSpyware.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Sophos.def_time | string | | 2018-12-06T00:52:00.000Z |
action_result.data.\*.scan_results.scan_details.Sophos.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Sophos.scan_time | numeric | | 2 |
action_result.data.\*.scan_results.scan_details.Sophos.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.TACHYON.def_time | string | | 2018-12-07T05:00:00.000Z |
action_result.data.\*.scan_results.scan_details.TACHYON.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.TACHYON.scan_time | numeric | | 17 |
action_result.data.\*.scan_results.scan_details.TACHYON.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Tencent.def_time | string | | 2015-05-18T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Tencent.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Tencent.scan_time | numeric | | 593 |
action_result.data.\*.scan_results.scan_details.Tencent.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.ThreatTrack.def_time | string | | 2018-12-05T08:10:00.000Z |
action_result.data.\*.scan_results.scan_details.ThreatTrack.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.ThreatTrack.scan_time | numeric | | 15 |
action_result.data.\*.scan_results.scan_details.ThreatTrack.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Total Defense.def_time | string | | 2018-12-06T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Total Defense.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Total Defense.scan_time | numeric | | 5 |
action_result.data.\*.scan_results.scan_details.Total Defense.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.TrendMicro House Call.def_time | string | | 2018-12-05T02:00:00.000Z |
action_result.data.\*.scan_results.scan_details.TrendMicro House Call.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.TrendMicro House Call.scan_time | numeric | | 424 |
action_result.data.\*.scan_results.scan_details.TrendMicro House Call.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.TrendMicro.def_time | string | | 2018-12-05T02:00:00.000Z |
action_result.data.\*.scan_results.scan_details.TrendMicro.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.TrendMicro.scan_time | numeric | | 351 |
action_result.data.\*.scan_results.scan_details.TrendMicro.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Vir.IT ML.def_time | string | | 2018-12-05T14:46:00.000Z |
action_result.data.\*.scan_results.scan_details.Vir.IT ML.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Vir.IT ML.scan_time | numeric | | 8 |
action_result.data.\*.scan_results.scan_details.Vir.IT ML.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Vir.IT eXplorer.def_time | string | | 2018-12-06T14:46:00.000Z |
action_result.data.\*.scan_results.scan_details.Vir.IT eXplorer.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Vir.IT eXplorer.scan_time | numeric | | 11 |
action_result.data.\*.scan_results.scan_details.Vir.IT eXplorer.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.VirIT.def_time | string | | 2015-05-15T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.VirIT.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.VirIT.scan_time | numeric | | 218 |
action_result.data.\*.scan_results.scan_details.VirIT.threat_found | string | | Win32.Parite.B |
action_result.data.\*.scan_results.scan_details.VirusBlokAda.def_time | string | | 2018-12-06T15:16:00.000Z |
action_result.data.\*.scan_results.scan_details.VirusBlokAda.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.VirusBlokAda.scan_time | numeric | | 29 |
action_result.data.\*.scan_results.scan_details.VirusBlokAda.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Webroot SMD.def_time | string | | 2021-01-28T21:00:16.000Z |
action_result.data.\*.scan_results.scan_details.Webroot SMD.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.Webroot SMD.scan_time | numeric | | 11 |
action_result.data.\*.scan_results.scan_details.Webroot SMD.threat_found | string | | Malware |
action_result.data.\*.scan_results.scan_details.Windows Defender.def_time | string | | 2021-01-29T00:29:58.000Z |
action_result.data.\*.scan_results.scan_details.Windows Defender.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Windows Defender.scan_time | numeric | | 154 |
action_result.data.\*.scan_results.scan_details.Windows Defender.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Xvirus Personal Guard.def_time | string | | 2018-12-06T10:47:00.000Z |
action_result.data.\*.scan_results.scan_details.Xvirus Personal Guard.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Xvirus Personal Guard.scan_time | numeric | | 62 |
action_result.data.\*.scan_results.scan_details.Xvirus Personal Guard.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Zillya!.def_time | string | | 2018-12-06T17:10:00.000Z |
action_result.data.\*.scan_results.scan_details.Zillya!.scan_result_i | numeric | | 0 |
action_result.data.\*.scan_results.scan_details.Zillya!.scan_time | numeric | | 22 |
action_result.data.\*.scan_results.scan_details.Zillya!.threat_found | string | | |
action_result.data.\*.scan_results.scan_details.Zoner.def_time | string | | 2015-05-14T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.Zoner.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.Zoner.scan_time | numeric | | 202 |
action_result.data.\*.scan_results.scan_details.Zoner.threat_found | string | | Win32.Parite.B |
action_result.data.\*.scan_results.scan_details.nProtect.def_time | string | | 2015-05-15T00:00:00.000Z |
action_result.data.\*.scan_results.scan_details.nProtect.scan_result_i | numeric | | 1 |
action_result.data.\*.scan_results.scan_details.nProtect.scan_time | numeric | | 94 |
action_result.data.\*.scan_results.scan_details.nProtect.threat_found | string | | Virus/W32.Parite.C |
action_result.data.\*.scan_results.start_time | string | | 2018-12-07T13:53:12.187Z |
action_result.data.\*.scan_results.total_avs | numeric | | 35 |
action_result.data.\*.scan_results.total_detected_avs | numeric | | 0 |
action_result.data.\*.scan_results.total_time | numeric | | 860 |
action_result.data.\*.share_file | numeric | | 1 |
action_result.data.\*.stored | boolean | | True |
action_result.data.\*.threat_name | string | | Trojan/Android!TOSD73es |
action_result.data.\*.votes.down | numeric | | 0 |
action_result.data.\*.votes.up | numeric | | 0 |
action_result.summary | string | | |
action_result.summary.file_result | string | | No Threat Detected |
action_result.message | string | | File result: No Threat Detected |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'test connectivity'

Validates the asset configuration for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
