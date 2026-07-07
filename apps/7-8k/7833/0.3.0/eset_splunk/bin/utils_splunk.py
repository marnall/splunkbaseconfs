import json
import typing as t
from datetime import datetime, timedelta, timezone
from pathlib import Path

from integration.utils import LastDataTimeHandler, TransformerData
from integration.models import DataSource, EnvVariables


class TransformerDetectionsSplunk(TransformerData):
    def __init__(self, env_vars: EnvVariables) -> None:
        super().__init__(env_vars)

    async def _send_data_to_destination(
        self, validated_data: t.List[dict[str, t.Any]], last_detection: t.Optional[str], *_: t.Any
    ) -> tuple[t.Optional[str], bool]:

        for item in validated_data:
            print(json.dumps(item))

        last_detection = max(validated_data, key=lambda detection: detection.get("occurTime")).get("occurTime")  # type: ignore
        return last_detection, True


class LastDataTimeHandlerSplunk(LastDataTimeHandler):
    def __init__(self, data_source: DataSource, interval: int) -> None:
        self._last_detection_file = Path(__file__).parent.joinpath(f"last_{data_source.name.lower()}.txt")
        super().__init__(data_source, interval)

    def get_last_data_time(self, data_source: DataSource, interval: int = 5) -> tuple[str, str]:
        if not self._last_detection_file.exists():
            if data_source == DataSource.INCIDENTS:
                return (datetime.now(timezone.utc) - timedelta(seconds=interval * 60)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ), ""
            else:
                return "", ""

        return self._last_detection_file.read_text(), ""

    async def update_last_data_time(self, cur_ld_time: t.Optional[str], *_: t.Any) -> None:
        self._last_detection_file.write_text(cur_ld_time)
