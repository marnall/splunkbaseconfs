## Playbook Backward Compatibility

- In version 3.0.0 of the connector, the API endpoints were updated from V2 to V3. Additionally, below three new parameters were added to the actions **'hunt ip', 'hunt file', 'hunt email', 'hunt domain',** and **'hunt url'**:

  - **attribute** - Retrieves Indicator attributes (default: **false**).
  - **tag** - Retrieves Indicator tags (default: **false**).
  - **security label** - Retrieves Indicator security labels (default: **false**).

- As a result, the output data paths have been updated. To ensure your existing playbooks function correctly, please **update, reinsert, modify, or delete** the affected action blocks accordingly.

### Asset Configuration Update

- The **base_url** parameter in the asset configuration should be set according to your ThreatConnect instance. Examples:

  - `https://api.threatconnect.com`
  - `https://sandbox.threatconnect.com`
  - `https://companyabc.threatconnect.com/api`

- For more details, please refer to the [ThreatConnect API documentation](https://docs.threatconnect.com/en/latest/rest_api/quick_start.html#using-the-api).
