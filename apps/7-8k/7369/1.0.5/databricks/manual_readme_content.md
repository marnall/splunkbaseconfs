## Authentication

There are two ways to configure authentication for the Databricks connector:

- Provide the same `username` and `password` you use to access the Databricks UI, and leave the `token` field blank.
- Generate and provide a `token` **[recommended]**:
  1. Navigate to your Databricks instance and log in.
  1. Click on your profile picture in the top right, and click on `Settings`.
  1. Click `Developer` in the menu on left. Next to `Access tokens`, click `Manage`.
  1. Click `Generate token`. Give your token a name and lifespan, and save it.
  1. Copy the token, and enter it in the `token` field when configuring the connector. Leave the `username` and `password` fields blank.
