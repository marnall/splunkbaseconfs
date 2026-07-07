# Pipl

Publisher: Splunk Community \
Connector Version: 3.0.1 \
Product Vendor: Pipl \
Product Name: Pipl \
Minimum Product Version: 5.1.0

This app integrates with Pipl to perform an investigative action

### Configuration variables

This table lists the configuration variables required to operate Pipl. These variables are specified when configuring a Pipl asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_key** | required | password | API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate API Key with Pipl server \
[get user](#action-get-user) - Get information about a person

## action: 'test connectivity'

Validate API Key with Pipl server

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get user'

Get information about a person

Type: **investigate** \
Read only: **True**

Please enter all the information you have about the person you're searching for. At least one field is required: Email, Phone, Username, Url, Name (First + Last), or Full Address (House Number + Street + City + State).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**first_name** | optional | First Name | string | |
**last_name** | optional | Last Name | string | |
**email** | optional | Email | string | `email` |
**phone** | optional | Phone Number | string | `phone` |
**username** | optional | Username | string | `user name` |
**url** | optional | URL | string | `url` |
**street** | optional | Street Name | string | |
**house_number** | optional | House Number | string | |
**city** | optional | City | string | |
**zip_code** | optional | Zip Code | string | |
**state** | optional | State Abbreviation | string | |
**country** | optional | Country Abbreviation | string | |
**age** | optional | Age (Exact Age or Range) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.age | string | | 35 26-29 |
action_result.parameter.city | string | | Smallville |
action_result.parameter.country | string | | US |
action_result.parameter.email | string | `email` | clark.kent@example.com |
action_result.parameter.first_name | string | | Clark |
action_result.parameter.house_number | string | | 10 |
action_result.parameter.last_name | string | | Kent |
action_result.parameter.phone | string | `phone` | +1 (999) 888-777 |
action_result.parameter.state | string | | KS |
action_result.parameter.street | string | | Hickory Lane |
action_result.parameter.url | string | `url` | https://www.linkedin.com/pub/superman/20/7a/365 |
action_result.parameter.username | string | `user name` | superman |
action_result.parameter.zip_code | string | | 66605 |
action_result.data.\*.available_data.basic.addresses | numeric | | 2 35 |
action_result.data.\*.available_data.basic.dobs | numeric | | 1 |
action_result.data.\*.available_data.basic.educations | numeric | | 2 5 |
action_result.data.\*.available_data.basic.emails | numeric | | 4 |
action_result.data.\*.available_data.basic.ethnicities | numeric | | 3 |
action_result.data.\*.available_data.basic.genders | numeric | | 1 16 |
action_result.data.\*.available_data.basic.images | numeric | | 2 9 |
action_result.data.\*.available_data.basic.jobs | numeric | | 3 34 |
action_result.data.\*.available_data.basic.landline_phones | numeric | | 1 8 |
action_result.data.\*.available_data.basic.languages | numeric | | 1 18 |
action_result.data.\*.available_data.basic.mobile_phones | numeric | | 8 |
action_result.data.\*.available_data.basic.names | numeric | | 3 25 |
action_result.data.\*.available_data.basic.origin_countries | numeric | | 1 |
action_result.data.\*.available_data.basic.phones | numeric | | 1 16 |
action_result.data.\*.available_data.basic.relationships | numeric | | 6 29 |
action_result.data.\*.available_data.basic.social_profiles | numeric | | 2 15 |
action_result.data.\*.available_data.basic.user_ids | numeric | | 1 24 |
action_result.data.\*.available_data.basic.usernames | numeric | | 2 5 |
action_result.data.\*.available_data.premium.addresses | numeric | | 2 56 |
action_result.data.\*.available_data.premium.dobs | numeric | | 1 2 |
action_result.data.\*.available_data.premium.educations | numeric | | 2 7 |
action_result.data.\*.available_data.premium.emails | numeric | | 4 23 |
action_result.data.\*.available_data.premium.ethnicities | numeric | | 3 |
action_result.data.\*.available_data.premium.genders | numeric | | 1 16 |
action_result.data.\*.available_data.premium.images | numeric | | 2 9 |
action_result.data.\*.available_data.premium.jobs | numeric | | 3 42 |
action_result.data.\*.available_data.premium.landline_phones | numeric | | 1 14 |
action_result.data.\*.available_data.premium.languages | numeric | | 1 18 |
action_result.data.\*.available_data.premium.mobile_phones | numeric | | 14 |
action_result.data.\*.available_data.premium.names | numeric | | 3 25 |
action_result.data.\*.available_data.premium.origin_countries | numeric | | 1 |
action_result.data.\*.available_data.premium.phones | numeric | | 1 28 |
action_result.data.\*.available_data.premium.relationships | numeric | | 6 29 |
action_result.data.\*.available_data.premium.social_profiles | numeric | | 3 30 |
action_result.data.\*.available_data.premium.user_ids | numeric | | 1 37 |
action_result.data.\*.available_data.premium.usernames | numeric | | 2 6 |
action_result.data.\*.available_sources | numeric | | 3 45 |
action_result.data.\*.http_status_code | numeric | | 200 |
action_result.data.\*.people.\*.addresses.\*.apartment | string | | 355 |
action_result.data.\*.people.\*.addresses.\*.city | string | | Metropolis |
action_result.data.\*.people.\*.addresses.\*.country | string | | US |
action_result.data.\*.people.\*.addresses.\*.display | string | | 1000-355 Broadway, Metropolis, Kansas |
action_result.data.\*.people.\*.addresses.\*.house | string | | 1000 |
action_result.data.\*.people.\*.addresses.\*.last_seen | string | | |
action_result.data.\*.people.\*.addresses.\*.po_box | string | | |
action_result.data.\*.people.\*.addresses.\*.state | string | | KS |
action_result.data.\*.people.\*.addresses.\*.street | string | | Broadway |
action_result.data.\*.people.\*.addresses.\*.type | string | | work |
action_result.data.\*.people.\*.addresses.\*.valid_since | string | | |
action_result.data.\*.people.\*.addresses.\*.zip_code | string | | 66605 |
action_result.data.\*.people.\*.dob.date_range.end | string | | 1987-05-13 |
action_result.data.\*.people.\*.dob.date_range.start | string | | 1986-01-01 |
action_result.data.\*.people.\*.dob.display | string | | 31 years old |
action_result.data.\*.people.\*.dob.valid_since | string | | |
action_result.data.\*.people.\*.educations.\*.date_range.end | string | | 2008-05-14 |
action_result.data.\*.people.\*.educations.\*.date_range.start | string | | 2005-09-01 |
action_result.data.\*.people.\*.educations.\*.degree | string | | B.Sc Advanced Science |
action_result.data.\*.people.\*.educations.\*.display | string | | B.Sc Advanced Science from University (2005-2008) |
action_result.data.\*.people.\*.educations.\*.school | string | | University |
action_result.data.\*.people.\*.emails.\*.address | string | `email` | clark.kent@test.com |
action_result.data.\*.people.\*.emails.\*.address_md5 | string | `md5` | eb3e11de3c9cefc2d9d70972350e2b28 |
action_result.data.\*.people.\*.emails.\*.disposable | boolean | | True False |
action_result.data.\*.people.\*.emails.\*.email_provider | boolean | | True False |
action_result.data.\*.people.\*.emails.\*.type | string | | work |
action_result.data.\*.people.\*.ethnicities.\*.content | string | | other |
action_result.data.\*.people.\*.gender.content | string | | male |
action_result.data.\*.people.\*.gender.valid_since | string | | |
action_result.data.\*.people.\*.id | string | | 052062d9-fdd8-4ba0-8565-9a9f65d7948b |
action_result.data.\*.people.\*.images.\*.url | string | `url` | http://test.com/superman/images/profile.jpg |
action_result.data.\*.people.\*.images.\*.valid_since | string | | |
action_result.data.\*.people.\*.jobs.\*.date_range.end | string | | 2012-10-09 |
action_result.data.\*.people.\*.jobs.\*.date_range.start | string | | 2000-12-08 |
action_result.data.\*.people.\*.jobs.\*.display | string | | Field Reporter at The Daily Planet (2000-2012) |
action_result.data.\*.people.\*.jobs.\*.industry | string | | Journalism |
action_result.data.\*.people.\*.jobs.\*.organization | string | | The Daily Planet |
action_result.data.\*.people.\*.jobs.\*.title | string | | Field Reporter |
action_result.data.\*.people.\*.languages.\*.display | string | | en_US |
action_result.data.\*.people.\*.languages.\*.inferred | boolean | | |
action_result.data.\*.people.\*.languages.\*.language | string | | en |
action_result.data.\*.people.\*.languages.\*.region | string | | US |
action_result.data.\*.people.\*.match | numeric | | |
action_result.data.\*.people.\*.names.\*.display | string | | Kal El |
action_result.data.\*.people.\*.names.\*.first | string | | Kal |
action_result.data.\*.people.\*.names.\*.last | string | | El |
action_result.data.\*.people.\*.names.\*.last_seen | string | | |
action_result.data.\*.people.\*.names.\*.middle | string | | Joseph |
action_result.data.\*.people.\*.names.\*.prefix | string | | |
action_result.data.\*.people.\*.names.\*.type | string | | |
action_result.data.\*.people.\*.names.\*.valid_since | string | | |
action_result.data.\*.people.\*.origin_countries.\*.country | string | | US |
action_result.data.\*.people.\*.origin_countries.\*.inferred | boolean | | |
action_result.data.\*.people.\*.phones.\*.country_code | numeric | | 1 |
action_result.data.\*.people.\*.phones.\*.display | string | `phone` | 978-555-0145 |
action_result.data.\*.people.\*.phones.\*.display_international | string | `phone` | +1 978-555-0145 |
action_result.data.\*.people.\*.phones.\*.do_not_call | boolean | | |
action_result.data.\*.people.\*.phones.\*.last_seen | string | | |
action_result.data.\*.people.\*.phones.\*.number | numeric | | 9785550145 |
action_result.data.\*.people.\*.phones.\*.type | string | | home_phone |
action_result.data.\*.people.\*.phones.\*.valid_since | string | | |
action_result.data.\*.people.\*.relationships.\*.emails.\*.address | string | `email` | jkent@example.com |
action_result.data.\*.people.\*.relationships.\*.emails.\*.address_md5 | string | `md5` | e81b8844517b6ab307a9e0fdf973ae3a |
action_result.data.\*.people.\*.relationships.\*.emails.\*.disposable | boolean | | True False |
action_result.data.\*.people.\*.relationships.\*.emails.\*.email_provider | boolean | | True False |
action_result.data.\*.people.\*.relationships.\*.names.\*.display | string | | Jonathan Kent |
action_result.data.\*.people.\*.relationships.\*.names.\*.first | string | | Jonathan |
action_result.data.\*.people.\*.relationships.\*.names.\*.last | string | | Kent |
action_result.data.\*.people.\*.relationships.\*.names.\*.middle | string | | Joseph |
action_result.data.\*.people.\*.relationships.\*.names.\*.type | string | | |
action_result.data.\*.people.\*.relationships.\*.subtype | string | | Adoptive Father |
action_result.data.\*.people.\*.relationships.\*.type | string | | family |
action_result.data.\*.people.\*.search_pointer | string | | f2f07638ed83d089405fb187df0fa9190a5bd6a9ec12a09190e783e903c035f9baa1008e7b3a2370575a740b4079e5f170cf5bf42974d9758deb7403fc639b71a2a360d9ea32e0e7b0c51de113525c290d87ae10df945c6e15b46fe3698addb356325840ff0431ba8a7bd1ce7dca7830492b1f559b6b436a5e15977f12c85bc54960e2f1d25ce2e5f8e5628e9472c94314a3deb105e2acfcddebf9a4d69adf9f9bdc32267dd1783da4e3b97107ef3da92edcf0c93b96bb9e299a7c568e3d1712184b40e11259f6d45a94b402065185e1ecccc48a2b169c14b822a23e5e98aeaf1b7cade0e5f20657b864a3425b8d7017ffc70cf4bd8ee1cba11503b323c6e4a774ed9342c0218da7e0309291317ec22128c000fa947657b38fce0358afc03ae2e1c47e37304fd371b4e19b0b971d99f381ba77d04d01bfcbf3089f9c2447e0f61a1d817324b59e863b000871a8eb4a3d3513265ef1ef0206f48b350b122257efd2c18b21b1b4d5f99b20fac5aa01bf8c124abf212a69867a16c90056b8ee0c8c54ac84fc01ae6aace0d85646640f0edc3d230e03a0eaffcf6f314d9d6b89268d4c53e5b167003027712c1c76c6d4b33d267519aeae54f775d5f7699ab3425f80a3d19de2ad60f26268384f91b4f2621b79653cc48aca7103c0ebb7e61fc38395b0cf19603e92ee4a946fe5c67357cc3166f75bfb2ca6acb977364374699110a6ffddc482886c4b502a045b6fac83f0373388dbce345004af3d3bab69d202baed27ae65cb1c780e567bb1239414615c513804c5cf24f8b9b2c3f25474c6a6275b5cb904e4789f7e44fe300918376ce62758d1fd49f7d823d821877bb9249c1122254304b125455d59ba51da5d397d669d6945e544880c7d9ccb292c58bebf8b1166c0b2ba3006f1d32c75f658417fa2278dbd3b10c0fdb21d9cc2141473d73db1e0a24f7d38215636af5bfafa86618a523c5f66c801bfce54153b2edf23f777593a45aacf0294c3484a8e7c24c81fde29ba6680a66832b336ce875465fc09526b5ab3bf0b5411cdbfcc45aac29e14f5bc1cc2e91301bd1566a8f63221f97b0cd01ee8bb5f20225f2b0a1919e648b2076f6436f6242c02626cbfc75a5a186fabb16d63348866ce566158627e1af9b05fe72748dc354fd8159fc0e469d0cb6cebc6524198ee4e3a832a81ff56e1db78239d706c68c0c5811ce01877bdf1b1d7a2521a5bf297eca8fb7da153870f29cb425753e04a766c7c69ab1f805dbcce5f7cea8a37af976c762d8879fbe9d4959e88474712438aacab3f62596f6622d9d8c9a44c58bb3f17844f67bc14052bd752bd9ff4c9c4234e1d25508361f52fa701aabe5d24a0ec0a1d0df6a6613184e2d231d5c7463a196699ba4852f3772951129e1b7beb359003c7b185ad2bec31c022c24f57fac0e26e2929d788bfda8c719791ae21845b4499671e6277b603fab7290c023aff4b524511817495f7ed2502a8527daa655a20c20babdb33afbc927776c8982c0aa30adcf454c9aa447dbaa632259b4fdbaa8fffefb96eee8ee96b36fb3e2e1cdfa0f93150f307b88f5c513d6b89102fab2780d115f83b453427b478b27022a1fc1d6674e34e64c4b53e1539f40856cd7ffdc22bd2dfb7acb056b56bf649e69e8f66ce5d147682e0473d4db231a6293b46bfcd0bc7a89d1a24c4d057c46b7493602575d2667faf6bbe4c8296b7183d |
action_result.data.\*.people.\*.urls.\*.category | string | | professional_and_business |
action_result.data.\*.people.\*.urls.\*.domain | string | `domain` | test.com |
action_result.data.\*.people.\*.urls.\*.name | string | | Test |
action_result.data.\*.people.\*.urls.\*.source_id | string | `md5` | edc6aa8fa3f211cfad7c12a0ba5b32f4 |
action_result.data.\*.people.\*.urls.\*.url | string | `url` | http://test.com/clark |
action_result.data.\*.people.\*.user_ids.\*.content | string | | 11231@test |
action_result.data.\*.people.\*.user_ids.\*.last_seen | string | | |
action_result.data.\*.people.\*.user_ids.\*.valid_since | string | | |
action_result.data.\*.people.\*.usernames.\*.content | string | | superman@home |
action_result.data.\*.people.\*.usernames.\*.last_seen | string | | |
action_result.data.\*.persons_count | numeric | | 1 18 |
action_result.data.\*.query.addresses.\*.country | string | | US |
action_result.data.\*.query.addresses.\*.display | string | | US KS Hickory Lane 10 SMALLVILLE |
action_result.data.\*.query.addresses.\*.house | string | | 10 |
action_result.data.\*.query.addresses.\*.state | string | | KS |
action_result.data.\*.query.addresses.\*.street | string | | Hickory Lane |
action_result.data.\*.query.addresses.\*.zip_code | string | | SMALLVILLE |
action_result.data.\*.query.dob.date_range.end | string | | 1991-12-19 |
action_result.data.\*.query.dob.date_range.start | string | | 1987-12-20 |
action_result.data.\*.query.dob.display | string | | 26-29 years old |
action_result.data.\*.query.emails.\*.address | string | `email` | clark.kent@example.com |
action_result.data.\*.query.emails.\*.address_md5 | string | `md5` | 2610ee49440fe757e3cc4e46e5b40819 |
action_result.data.\*.query.emails.\*.type | string | | |
action_result.data.\*.query.names.\*.display | string | | Clark Kent |
action_result.data.\*.query.names.\*.first | string | | Clark |
action_result.data.\*.query.names.\*.last | string | | Kent |
action_result.data.\*.query.user_ids.\*.content | string | | 11231@test |
action_result.data.\*.query.usernames.\*.content | string | | superman |
action_result.data.\*.search_id | string | | 0 1712200002322982354608353166572731455 |
action_result.data.\*.visible_sources | numeric | | 2 0 |
action_result.data.\*.warnings | string | | City `Smallville` does not exist in provided state KS. It is ignored. |
action_result.summary.exact_match_found | boolean | | True False |
action_result.summary.possible_matches | numeric | | 18 |
action_result.message | string | | Exact match found: True Possible matches: 18, Exact match found: False |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

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
