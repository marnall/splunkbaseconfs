import json
import logging
import sys
import traceback
import pytz
from datetime import datetime, timedelta
from solnlib import conf_manager, log
from splunklib import modularinput as smi
from solnlib.modular_input import checkpointer
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.git.models import GitPullRequestSearchCriteria, GitPushSearchCriteria

ADDON_NAME = "Azure_DevOps_TA_nxtp"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_config_property(session_key: str, config: str, identifier: str, key: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{config}",
    )
    conf_file = cfm.get_conf(f"{config}")
    return conf_file.get(identifier).get(key)


class Input(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("azure_devops_git_commits")
        scheme.description = "azure_devops_git_commits input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument("name", title="Name", description="Name", required_on_create=True)
        )
        scheme.add_argument(
            smi.Argument(
                "start_from",
                title="Start From",
                description="",
                required_on_create=False,
                required_on_edit=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        session_key = self._input_definition.metadata["session_key"]
        organization = get_config_property(
            session_key, f"{ADDON_NAME.lower()}_settings", "additional_parameters", "organization"
        )
        connection = Connection(
            base_url=f"https://dev.azure.com/{organization}",
            creds=BasicAuthentication(
                "",
                get_config_property(
                    session_key,
                    f"{ADDON_NAME.lower()}_settings",
                    "additional_parameters",
                    "pat",
                ),
            ),
        )
        core_client = connection.clients.get_core_client()
        git_client = connection.clients.get_git_client()
        pull_request_search_criteria = GitPullRequestSearchCriteria(status="all")
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            logger = logger_for_input(normalized_input_name)
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name=f"{ADDON_NAME.lower()}_settings",
            )
            try:
                logger.setLevel(log_level)
                log.modular_input_start(logger, normalized_input_name)
                checkpoint = checkpointer.KVStoreCheckpointer(input_name, session_key, ADDON_NAME)
                # checkpoint = checkpointer.FileCheckpointer(checkpoint_dir=str(Path.cwd().parent/"local"))
                last_fetch = checkpoint.get("last_fetch_pr")
                logger.info(f"Last fetch: {last_fetch}")
                if last_fetch is None:
                    start_from_config = get_config_property(
                        session_key, "inputs", input_name, "start_from"
                    )
                    start_from = (
                        datetime.strptime(str(start_from_config), "%Y-%m-%d %H:%M:%S")
                        if start_from_config is not None
                        else datetime.now() - timedelta(days=30)
                    )
                else:
                    start_from = datetime.fromtimestamp(last_fetch)

                timezone = pytz.timezone("UTC")
                get_config_property(session_key, "inputs", input_name, "index")
                logger.info(
                    f"Start running '{normalized_input_name}' from {start_from} till {datetime.now(tz=timezone)}"
                )
                commits = []  # unique collection of commit IDs to avoid duplicates
                pushes = []  # unique collection of push IDs to avoid duplicates
                start_from = timezone.localize(start_from)
                git_push_search_criteria = GitPushSearchCriteria(from_date=start_from)
                new_start_from = datetime.now().timestamp()
                for project in core_client.get_projects():
                    logger.info(f"Fetching {normalized_input_name} for {project.name}.")
                    for repo in git_client.get_repositories(project=project.id):
                        logger.debug(f"Processing repository '{repo.name}' in '{project.name}'.")
                        for pull_request in git_client.get_pull_requests(
                            project=project.id,
                            repository_id=repo.id,
                            search_criteria=GitPullRequestSearchCriteria(status="all"),
                        ):
                            logger.debug(
                                f"Processing '{project.name}' - '{repo.name}' pull request '{pull_request.pull_request_id}'."
                            )
                            for thread in git_client.get_threads(
                                repository_id=repo.id, pull_request_id=pull_request.pull_request_id
                            ):
                                if thread.last_updated_date.timestamp() < start_from.timestamp():
                                    continue
                                for comment in thread.comments:
                                    if (
                                        comment.last_updated_date.timestamp()
                                        < start_from.timestamp()
                                        or not "@" in comment.author.unique_name
                                    ):
                                        continue
                                    event_writer.write_event(
                                        smi.Event(
                                            source=f"{input_name}:{organization}",
                                            sourcetype="azure:devops:pr:"
                                            + (
                                                "comment"
                                                if comment.comment_type == "text"
                                                else "activity"
                                            ),
                                            host="dev.azure.com",
                                            data=json.dumps(
                                                {
                                                    "project_id": project.id,
                                                    "pull_request_id": pull_request.pull_request_id,
                                                    "pull_request_name": pull_request.title,
                                                    "project_name": project.name,
                                                    "repository_id": repo.id,
                                                    "repository_name": repo.name,
                                                    "user_email": comment.author.unique_name,
                                                    "user_name": comment.author.display_name,
                                                    "creation_date": comment.published_date.timestamp(),
                                                    "content": comment.content,
                                                }
                                            ),
                                        )
                                    )
                        logger.info(
                            f"Finished processing '{project.name}' repository '{repo.name}'."
                        )
                    logger.info(f"Finished processing project '{project.name}'.")
                logger.info(f"Finished processing all Git events.")
                log.modular_input_end(logger, normalized_input_name)
                checkpoint.update("last_fetch_pr", new_start_from)
            except Exception as e:
                logger.error(
                    f"Exception raised while ingesting data for "
                    f"{normalized_input_name}: {e}. Traceback: "
                    f"{traceback.format_exc()}"
                )


if __name__ == "__main__":
    exit_code = Input().run(sys.argv)
    sys.exit(exit_code)
