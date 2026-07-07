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
        scheme = smi.Scheme("azure_devops_build")
        scheme.description = "azure_devops_build input"
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
        connection = Connection(
            base_url=f"https://dev.azure.com/{get_config_property(session_key, f'{ADDON_NAME.lower()}_settings', 'additional_parameters', 'organization')}",
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
        build_client = connection.clients.get_build_client()
        timezone = pytz.timezone("UTC")
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
                last_fetch = checkpoint.get("last_fetch_build")
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

                start_from = timezone.localize(start_from)
                new_start_from = datetime.now().timestamp()
                index = get_config_property(session_key, "inputs", input_name, "index")
                logger.info(
                    f"Start fetching '{normalized_input_name}' from {start_from} till {datetime.now(tz=timezone)}"
                )
                for project in core_client.get_projects():
                    logger.info(f"Fetching {normalized_input_name} for {project.name}.")
                    builds = build_client.get_builds(project=project.id, min_time=start_from)
                    for build in builds:
                        data = process_build(
                            project=build.project, build=build, repo=build.repository
                        )
                        logger.debug(f"About to write Event: {data}")
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(data, ensure_ascii=False),
                                index=index,
                                sourcetype="azure:devops:build",
                                host="dev.azure.com",
                                # time=datetime.strptime(data["startTime"].split("+")[0],"%Y-%m-%d %H:%M:%S.%N").timestamp()
                            )
                        )
                log.modular_input_end(logger, normalized_input_name)
                checkpoint.update("last_fetch_build", new_start_from)
            except Exception as e:
                logger.error(
                    f"Exception raised while ingesting data for {normalized_input_name}: {e}. Traceback: {traceback.format_exc()}"
                )


def process_build(project, build, repo):
    build_dump = {
        "build_id": build.id,
        "definition": build.definition.name,
        "project_id": project.id,
        "project_name": project.name,
        "repository_id": repo.id,
        "repository_name": repo.name,
        "status": str(build.status.title()),
        "finishTime": str(build.finish_time),
        "startTime": str(build.start_time),
        "uri": build.uri,
        "result": build.result,
        "sourceBranch": build.source_branch,
        "sourceVersion": build.source_version,
        "buildReason": build.reason,
        "logID": build.logs.id,
        "logURL": build.logs.url,
        "requestedBy": build.requested_by.display_name,
        "requestedFor": build.requested_for.display_name,
        # "author_email": commit.author.email,
        # "author_name": commit.author.name,
        # "user_email": commit.committer.email,
        # "user_name": commit.committer.name,
        # "push_id": push.push_id,
        # "push_date": push.date.timestamp(),
        # "creation_date": commit.author.date.timestamp(),
    }
    return build_dump


if __name__ == "__main__":
    exit_code = Input().run(sys.argv)
    sys.exit(exit_code)
