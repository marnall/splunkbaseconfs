## Contributing

For more information about contributing to Splunk SOAR Apps please take a look at our app [Contribution Guide](https://github.com/splunk-soar-connectors/.github/blob/main/.github/CONTRIBUTING.md)!

## Set up your development environment

You'll need a Phantom OVA VM image to run this application. To download the image, first
register [here](https://my.phantom.us/signup/)
to create a Phantom account. Phantom will approve your registration and send you credentials for https://my.phantom.us.

Next, log in and go [here](https://my.phantom.us/downloads/) to download the Phantom VM image.

Follow these [instructions](https://docs.splunk.com/Documentation/Phantom/4.10.3/Install/InstallOVA) to install Splunk
Phantom as a VM image. You do NOT need to complete the section labeled "Configure the network settings for the virtual
machine".

Use these [default credentials](https://docs.splunk.com/Documentation/Phantom/4.10.3/Install/Reference) to log in.
Confirm that you can connect to the VM via SSH on your host machine. You can use `hostname -I` on the remote machine to
look up your IP address. Also confirm that you can access the Phantom web app at `https://{phantom_VM_IP_address}`.

NOTE: If you are consistently getting timeouts connecting to the Phantom VM, try disconnecting from the VPN and
re-attempting.

### Style linter

When you open a PR, a series of style checks will run. See the [pre-commit-config.yaml](.pre-commit-config.yaml) file to
see a list of the projects involved in this automation. If your code does not pass the style checks, the PR will not be
allowed to merge. Many of the style rules can be corrected automatically by running a simple command once you are
satisfied with your change:

```bash
make style
```

This will output a diff of the files that were changed. Once these have been corrected and re-pushed, the PR checks
should pass.

You can also choose to have these checks / automatic adjustments occur automatically on each git commit that you make (
instead of only when running `make style`.) To do so, install the pre-commit hooks:

```bash
pre-commit install
```

## Deploying the app

To test the Code42 Phantom app, you must deploy it to a running Phantom VM and run a compilation script on that VM.

Run the below command to install the Code42 app on Phantom.

```bash
export PHANTOM_VM_IP_ADDR=0.0.0.0  # Replace with IP address for Phantom VM
export PHANTOM_VM_PASSWORD=phantom  # Use the password for your phantom admin user.
make deploy
```

If you are working on macOS you can
install `sshpass` [here](https://stackoverflow.com/questions/32255660/how-to-install-sshpass-on-mac/62623099#62623099)
and bypass the VM SSH password prompts.

```bash
export PHANTOM_VM_IP_ADDR=0.0.0.0 # Replace with IP address for Phantom VM
export PHANTOM_PWD=password # Replace with password for phantom user on Phantom VM
make deploy-bypass
```

Open the Phantom web app and login as the `admin` user. Navigate to `Apps > Unconfigured Apps` and find the Code42 App.
Click Configure New Asset to supply the Console URL, username, and password to connect with. Fill out the fields in
Asset Info and Asset Settings. Save the Asset Configuration and then click Test Connectivity to test your connection.

## Unit Testing

### Creating a virtual environment

To run the unit tests you will need to create a Python virtual environment for the Phantom app and its dependencies.
Creating a virtual environment is *not* necessary to run or deploy the app to a Phantom VM. It's only necessary if you
want to run unit tests.

#### macOS

Install `pyenv` and `pyenv-virtualenv` via [homebrew](https://brew.sh/):

```bash
brew install pyenv pyenv-virtualenv
```

After installing `pyenv` and `pyenv-virtualenv`, be sure to add the following entries to your `.zshrc` (or `.bashrc` if
you are using bash) and restart your shell:

```bash
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

Then, create your virtual environment.

```bash
pyenv install 3.6.13
pyenv virtualenv 3.6.13 phantom
pyenv activate phantom
pip install --upgrade pip
```

Note: if the command `pyenv virtualenv 3.6.13 phantom` fails, try the following command instead:

```bash
pyenv install --patch 3.6.13 < <(curl -sSL https://github.com/python/cpython/commit/8ea6353.patch)
```

Use `source deactivate` to exit the virtual environment and `pyenv activate phantom` to reactivate it.

#### Windows/Linux

Install Python 3.6.13 from [python.org](https://python.org).

Next, in a directory somewhere outside the project, create and activate your virtual environment:

```bash
python -m venv phantom
# macOS/Linux
source phantom/bin/activate
# Windows
.\phantom\Scripts\Activate
pip install --upgrade pip
```

To leave the virtual environment, simply use:

```bash
deactivate
```

### Running a complete local build

Make sure you have created a Python virtual environment for the Phantom project as described above.

Then, activate the virtual environment and install the dependencies before running the build.

```bash
pip install -e .'[dev]'
make
```

By default, `make` will run all unit tests, Phantom configuration / lint validators, style checks, and create a local
tarball of the app.

Each of these commands can also be run individually if desired:

```bash
make clean
make test
make validate
make style
make deploy
make deploy-bypass
```

#### Running tests within a Phantom deployment

You can clone this repository directly onto a Phantom server and run the tests on it. When you do this, the tests will
use the Phantom SDK instead of the stubs this project has defined in the `stubs` folder:

```bash
phenv pip install -e . # note: exclude [dev] to skip installing the stubs
phenv pytest
```

If you accidentally install the stubs into the Phantom environment, you can remove them via:

```bash
phenv pip uninstall stubs
```

### Stubs

This app is built on top of several modules developed by Phantom. Since we don't have access to the source for these
modules, we've stubbed them out in the `phantom` directory so that they can be imported by the test code.

# Testing the App

First, get alerts into Phantom by going to your configured asset's Ingest Settings and enabling
polling. Then, hit `Poll Now`. You likely will want to increase the `Maximum Containers` and `Maximum Artifacts`
properties to ingest more alerts.

After the ingestion completes, go to the Sources tab and look at the newly ingested alerts.
Click on the alert and go to the "Analyst" view. Finally, use the "Action" and "Playbook" buttons
to run actions or playbooks.

## Reset Polling Checkpoint

To clear a last poll timestamp for a given asset, `ssh` into the server and go to the directory
`/opt/phantom/local_data/app_states/4d8f53a7-7b12-4d7d-8b01-6575680acf6f` (the last part is the Code42 app ID).

Then, find your state file. It is in the format `<asset-id>_state.json`. (Note: to find your asset ID, look
at the URL path's parameters when selecting assets on the "Asset Configuration" page).

To reset your timestamp, edit your state file (such as with `vi`) and set the property `last_time` to have a value
of `0`.

## Running the Playbook

To automatically run the `code42_alert_response_playbook` playbook on new Code42 Alerts, do the following:

1. Add a custom event label. Go to Administration -> Event Settings -> Label Settings.
   Create a new label named `code42 alerts`.

1. Activate the playbook by going to Playbooks -> `code42_alert_response_playbook` -> Edit Playbook ->
   Playbook Settings -> Active, and then enabling the switch.

1. Specify the ingest label on the Code42 App by going to Apps -> Code42 -> `<your asset>` -> Ingest Settings -> Edit.
   Where it says `Label to apply to objects from this source`, select `code42 alerts`

1. (optional) If you have enabled polling previously, you might want to delete events, reset your timestamp,
   and re-poll.

1. View a newly ingested security event. Notice the new event row's label column now says `code42 alerts`.
   Now, go into the alert and go to Analyst mode.

Notice that the playbook has started and is awaiting your response!
