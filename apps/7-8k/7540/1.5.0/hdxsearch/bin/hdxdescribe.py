#!/usr/bin/env python3

import sys
import os
from dataclasses import dataclass, asdict
from typing import Generator, Any, List, Dict
from errors import HdxCommandFatalError
from cluster_config import ClusterConfig
from app_version import build_admin_comment
from utils import format_bytes

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from sqlglot import exp

from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)


@dataclass(frozen=True)
class ColumnDescription:
    column_name: str
    column_type: str


@Configuration(type="reporting")
class HdxDescribe(GeneratingCommand):
    """
    hdxdescribe command describes the schema of HDX tables or lists all projects and tables.

    Examples:

        | hdxdescribe
        | hdxdescribe cluster="my_cluster"
        | hdxdescribe table="hydro.logs"
        | hdxdescribe project="hydro"
        | hdxdescribe cluster="my_cluster" table="hydro.logs"
        | hdxdescribe cluster="my_cluster" project="hydro"
    """

    cluster: str = Option(
        require=False,
        validate=validators.Fieldname(),
        doc="The name of the Hydrolix cluster to query. Defaults to the configured default cluster.",
    )
    table: str = Option(
        require=False,
        validate=validators.Fieldname(),
        doc="The Hydrolix table to describe in the form `project.table`. Mutually exclusive with 'project'.",
    )
    project: str = Option(
        require=False,
        validate=validators.Fieldname(),
        doc="A Hydrolix project name. Lists all tables in the project. Mutually exclusive with 'table'.",
    )

    def generate(self) -> Generator[Any, None, None]:
        try:
            if self.table and self.project:
                raise HdxDescribeFatalError("'table' and 'project' are mutually exclusive")
            if self.table:
                for col in self._describe_table():
                    yield asdict(col)
            else:
                for event in self._list_tables():
                    yield event
        except HdxCommandFatalError as err:
            self.error_exit(err.escaped())
            raise

    def _cluster_config(self) -> ClusterConfig:
        return ClusterConfig.from_service(self.service, self.cluster)

    def _settings(self) -> List[str]:
        return [f"hdx_query_admin_comment='{build_admin_comment(self.metadata.searchinfo)}'"]

    def _list_tables(self) -> Generator[Dict[str, Any], None, None]:
        conf = self._cluster_config()
        hdx_cli = conf.make_client(self.logger)
        settings = self._settings()

        if self.project:
            databases = [self.project]
        else:
            try:
                databases = hdx_cli.show_databases()
            except Exception as err:
                raise HdxDescribeFatalError(f"Failed to retrieve databases: {err}")

        try:
            for database in databases:
                try:
                    tables = hdx_cli.show_tables(database, settings=settings)
                except Exception as err:
                    raise HdxDescribeFatalError(f"Failed to retrieve tables for database '{database}': {err}")

                yield {"project": database, "tables": tables}
        finally:
            self.write_warning(f"Hydrolix bytes received: {format_bytes(hdx_cli.bytes_received)}")

    def _describe_table(self) -> Generator[ColumnDescription, None, None]:
        conf = self._cluster_config()
        hdx_cli = conf.make_client(self.logger)
        settings = self._settings()

        parsed = exp.to_table(self.table, dialect="clickhouse")
        if not parsed.db:
            raise HdxDescribeFatalError("Invalid table format. Expected 'project.table'")

        project = parsed.db
        table_name = parsed.name

        try:
            result = hdx_cli.describe_table_raw(project, table_name, settings=settings)
        except Exception as err:
            raise HdxDescribeFatalError(f"Failed to describe table '{project}.{table_name}': {err}")

        meta = result.get("meta", [])
        col_indices = {col["name"]: i for i, col in enumerate(meta)}

        required_fields = ["name", "type"]
        for field in required_fields:
            if field not in col_indices:
                raise HdxDescribeFatalError(f"Unexpected DESCRIBE TABLE response: missing '{field}' column")

        try:
            for row in result.get("data", []):
                yield ColumnDescription(
                    column_name=row[col_indices["name"]],
                    column_type=row[col_indices["type"]],
                )
        finally:
            self.write_warning(f"Hydrolix bytes received: {format_bytes(hdx_cli.bytes_received)}")


class HdxDescribeFatalError(HdxCommandFatalError):
    """
    An error that is enough on its own to terminate the describe command.
    """

    pass


dispatch(HdxDescribe, sys.argv, sys.stdin, sys.stdout, __name__)
