# Contributing to JenkinsAppRepo

## Overview

The project contains a variety of packages that are published and versioned collectively. Each package lives in its own
directory in the `/packages` directory. Each package is self contained, and defines its dependencies in a package.json file.

We use [Yarn Workspaces](https://yarnpkg.com/lang/en/docs/workspaces/) and [Lerna](https://github.com/lerna/lerna) for
managing and publishing multiple packages in the same repository.

## Getting Started

1.  Clone the repo.
2.  Install yarn (>= 1.2) if you haven't already: `npm install --global yarn`.
3.  (Optional) Setup your local mac devlopment env. `yarn run setup_mac_dev_env`.
4.  Run the setup task: `yarn run setup`.

After this step, the following tasks will be available:

-   `start` – Run the `start` task for each project
-   `build` – Create a production bundle for all projects
-   `build:dev` – Create a dev bundle for all projects
-   `test` – Run unit tests for each project
-   `lint` – Run JS and CSS linters for each project
-   `format` – Run prettier to auto-format `*.js`, `*.jsx` and `*.css` files. This command will overwrite files without
    asking, `format:verify` won't.

Running `yarn run setup` once is required to enable all other tasks. The command might take a few minutes to finish.

## Developer Scripts

Commands run from the root directory will be applied to all packages. This is handy when working on multiple packages
simultaneously. Commands can also be run from individual packages. This may be better for performance and reporting when
only working on a single package. All of the packages have similar developer scripts, but not all scripts are implemented
for every package. See the `package.json` of the package in question to see which scripts are available there.

For more granular control of development scripts, consider using [Lerna](https://github.com/lerna/lerna) directly.

## Code Formatting

JenkinsAppRepo uses [prettier](https://github.com/prettier/prettier) to ensure consistent code formatting. It is recommended
to [add a prettier plugin to your editor/ide](https://github.com/prettier/prettier#editor-integration).

## FAQ

1.  Why do I fail to setup my local mac development env?

-   **Answer**: usually, you will see the error message when you fail to setup dev env. If you get "You local env looks like a CI env. Please check the environment vars.", please check your local development environment, make sure you does not export any CI related env vars. For example, do not set these env vars (**CI, CONTINUOUS_INTEGRATION, BUILD_NUMBER, RUN_ID**) in your shell env. we use [is-ci](https://github.com/watson/is-ci) to check the env. If you get "git hook is not setup!", probably, you have some very specific env vars which prevents husky to install all the git hooks. Most of the env is related to CI system.
