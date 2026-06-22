import re

from llm_service import invoke_llm


def _option(command, explicit_value, name):
    if explicit_value is not None:
        return explicit_value
    return getattr(command, name, None)


PLACEHOLDER_PATTERN = re.compile(r"{([^{}]+)}")


def _render_prompt_template(prompt_template, record):
    def replace(match):
        field_name = match.group(1).strip()
        if not field_name:
            return ""

        value = record.get(field_name)
        if value is None or value == "":
            return ""
        return str(value)

    return PLACEHOLDER_PATTERN.sub(replace, str(prompt_template))


def stream(command, records, prompt=None, connection=None, model=None):
    prompt = _option(command, prompt, "prompt")
    connection = _option(command, connection, "connection")
    model = _option(command, model, "model")
    session_key = command.metadata.searchinfo.session_key

    if not prompt:
        raise ValueError("prompt is missing or empty")

    for record in records:
        rendered_prompt = _render_prompt_template(prompt, record)

        response_text = invoke_llm(
            session_key=session_key,
            prompt=rendered_prompt,
            requested_connection=connection,
            requested_model=model,
        )
        command.add_field(record, "llm_response", response_text)
        yield record
