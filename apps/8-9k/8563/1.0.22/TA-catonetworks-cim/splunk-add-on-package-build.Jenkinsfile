def SLACK_MAIN_CHANNEL = "eks-services-build-failures"
def SLACK_CHNG_CHANNEL = "auto-chng-tickets"

def APP_NAME = "TA-catonetworks-cim"
def SPLUNK_APPS_DIR = "services/events-log/cato-splunk-applications"
def ARTIFACTORY_REPO = "cato-splunk-applications"

def podYaml = k8sPodConfigGenerator(podTemplateVarName: "k8s-dind-arm")

pipeline {
    agent {
        kubernetes {
            cloud 'prod-ie1-maker'
            yaml podYaml
            defaultContainer 'jnlp'
        }
    }
    parameters {
        booleanParam(name: 'CREATE_OFFICIAL_BUILD', defaultValue: false, description: 'Create an official build with version bump and publish to Artifactory')
    }
    options {
        ansiColor('xterm')
        skipStagesAfterUnstable()
    }
    environment {
        REPO_NAME = "server-services"
        BRANCH = env.GIT_BRANCH.replaceFirst(".*/", "")
        TAG = "${BRANCH}_${env.BUILD_NUMBER}"
        GIT_MINI_SHA = env.GIT_COMMIT.trim().substring(0, 7)
        GIT_COMMIT_AUTHOR_NAME = sh(script: "git show -s --pretty=%an HEAD", returnStdout: true).trim()
    }

    stages {
        stage('Package') {
            steps {
                script {
                    dir(SPLUNK_APPS_DIR) {
                        def packageCmd = "./scripts/package-app.sh ${APP_NAME}"
                        if (shouldPublish()) {
                            packageCmd += " --bump-version ${env.BUILD_NUMBER}"
                        }
                        logger.info("Packaging app with command: ${packageCmd}")
                        sh packageCmd
                    }
                }
            }
        }

        stage('Setup AppInspect') {
            steps {
                script {
                    dir(SPLUNK_APPS_DIR) {
                        sh './splunk-appinspect-validator/setup-venv.sh'
                    }
                }
            }
        }

        stage('Validate') {
            steps {
                script {
                    dir(SPLUNK_APPS_DIR) {
                        def splFile = sh(
                            script: "ls -1 build/${APP_NAME}-*.spl | head -1",
                            returnStdout: true
                        ).trim()

                        if (!splFile) {
                            error "No .spl package found for ${APP_NAME} in build/"
                        }

                        logger.info("Validating: ${splFile}")
                        sh "./splunk-appinspect-validator/validate.sh '${splFile}' precert"
                    }
                }
            }
        }

        stage('Upload to Artifactory') {
            when {
                expression { return shouldPublish() }
            }
            steps {
                script {
                    dir(SPLUNK_APPS_DIR) {
                        def splFile = sh(
                            script: "ls -1 build/${APP_NAME}-*.spl | head -1",
                            returnStdout: true
                        ).trim()

                        def m = splFile =~ /${APP_NAME}-(.+)\.spl/
                        if (!m) { error "Cannot extract version from filename: ${splFile}" }
                        def version = m[0][1]

                        logger.info("Uploading ${splFile} to Artifactory (version: ${version})")

                        upload_to_artifactory(
                            fileName: splFile,
                            artifactoryRepository: ARTIFACTORY_REPO,
                            artifact: APP_NAME,
                            version: version,
                            artifactName: "${APP_NAME}-${version}.spl",
                            artifactoryUrl: "https://catonetworks.jfrog.io/artifactory"
                        )

                        echo "============================================"
                        echo "Published: https://catonetworks.jfrog.io/artifactory/${ARTIFACTORY_REPO}/${APP_NAME}/${version}/${APP_NAME}-${version}.spl"
                        echo "============================================"
                    }
                }
            }
        }
    }

    post {
        success {
            script {
                bitbucket_status_notifier(buildState: 'SUCCESSFUL', repoSlug: env.REPO_NAME, commitId: env.GIT_COMMIT)
            }
        }
        unsuccessful {
            script {
                bitbucket_status_notifier(buildState: 'FAILED', repoSlug: env.REPO_NAME, commitId: env.GIT_COMMIT)
            }
            slackSend channel: "${SLACK_MAIN_CHANNEL}", color: 'danger',
                message: "@${GIT_COMMIT_AUTHOR_NAME.split('@')[0].replaceAll(' ', '.').toLowerCase()} ${APP_NAME} build FAILED - (<${BUILD_URL}|more details>)"
        }
        always {
            script {
                currentBuild.description = "Author: ${GIT_COMMIT_AUTHOR_NAME};<br>Branch: ${BRANCH_NAME};<br>Sha: ${GIT_MINI_SHA};<br>App: ${APP_NAME}"
                currentBuild.displayName = "${BUILD_NUMBER} - ${TAG}"
            }
        }
    }
}

def shouldPublish() {
    return env.BRANCH_NAME ==~ /^production_.*/ || params.CREATE_OFFICIAL_BUILD
}
