
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging

util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""", 
            ), 
            validator.String(
                max_len=100, 
                min_len=1, 
            )
        )
    )
]

fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='3600',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""", 
            ), 
            validator.Number(
                max_val=86400, 
                min_val=10, 
            )
        )
    ), 
    field.RestField(
        'index',
        required=False,
        encrypted=False,
        default='default',
        validator=validator.IndexName()
    ), 
    field.RestField(
        'account',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'metrics',
        required=True,
        encrypted=False,
        default='human_risk_score,assignments_overdue,overdue_users',
        validator=validator.Pattern(
            regex=r"""^(human_risk_score|training_completion_rate|assignments_overdue|phishing_click_rate|phishing_report_rate|overdue_users|assignments_by_category|auto_assigned_via_grafana)(,(human_risk_score|training_completion_rate|assignments_overdue|phishing_click_rate|phishing_report_rate|overdue_users|assignments_by_category|auto_assigned_via_grafana))*$""", 
        )
    ), 
    field.RestField(
        'lookback_days',
        required=True,
        encrypted=False,
        default='30',
        validator=validator.Pattern(
            regex=r"""^([1-9][0-9]{0,2})$""", 
        )
    ), 
    field.RestField(
        'team',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'channel',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(email|sms)?$""", 
        )
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None, special_fields=special_fields)



endpoint = DataInputModel(
    'ransomleak_risk',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
