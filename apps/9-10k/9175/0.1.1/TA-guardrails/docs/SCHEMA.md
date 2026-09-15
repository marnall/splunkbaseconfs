# Normalized AI Guardrail Event Schema

**Version 0.1** · Reference implementation: TA-guardrails

This document specifies a vendor-neutral schema for AI guardrail and content
safety events, and its mapping onto the Splunk Common Information Model.

The schema is written to be implementable outside Splunk. The CIM mapping is a
separate section precisely so that the schema itself can be adopted by tools
that have no relationship to Splunk.

---

## 1. Problem

Guardrail systems — content filters, safety classifiers, policy engines, prompt
injection detectors — emit the same five facts:

1. Something was evaluated
2. Against a named policy
3. Belonging to a hazard or attack category
4. With some confidence or severity
5. Producing a verdict

Every vendor expresses those five facts differently. Bedrock nests typed policy
assessments in an array of arrays. Azure Content Safety returns integer severity
per category. Azure OpenAI returns per-category objects with string severity.
Vertex returns probability and severity as separate enums plus float scores.
Llama Guard returns a two-line string. Lakera returns parallel boolean and float
maps. NeMo returns a list of activated rails.

The result is that an organization running guardrails across two clouds cannot
answer "how many prompt injection attempts did we block this week" without
writing bespoke logic per provider. That is the gap this schema closes.

## 2. Event model

**One event per evaluation.** An evaluation is a single guardrail invocation
against a single input or output. An evaluation produces zero or more
**findings**.

**One finding per policy hit.** A finding is a single category with its own
severity and action.

This distinction matters and is frequently collapsed by implementations, which
is why counts are so often wrong. An evaluation that scores four content
categories and matches two PII entities is **one evaluation and six findings**.
Counting evaluations answers "how much traffic did we screen"; counting findings
answers "what did we find". Alerting on the wrong one produces either false
confidence or false alarm.

## 3. Event-level fields

| Field | Type | Description |
|---|---|---|
| `guardrail_vendor` | enum | Provider identifier. See §6. |
| `guardrail_id` | string | Policy or deployment identifier at the provider. |
| `guardrail_version` | string | Policy version, where the provider exposes one. |
| `direction` | enum | `input` or `output`. Required. See §4. |
| `guardrail_action` | enum | `blocked`, `anonymized`, `flagged`, `allowed`. |
| `action` | enum | CIM-constrained: `blocked` or `allowed`. |
| `category` | string | Normalized category of the most severe finding. §5. |
| `vendor_category` | string | Provider's own category name, preserved. |
| `guardrail_score` | int 0–100 | Normalized severity of the most severe finding. |
| `severity` | enum | CIM band derived from `guardrail_score`. |
| `signature` | string | `{vendor}:{categories}` — stable identifier for the policy hit. |
| `finding_count` | int | Number of findings in this evaluation. |
| `model` | string | Model the evaluation protected. |
| `app` | string | Application or deployment name. |
| `user` | string | Calling principal. |
| `src` | string | Source address of the caller. |
| `dest` | string | Guardrail service endpoint. |
| `request_id` | string | Provider correlation identifier. |

### Derived analyst fields

| Field | Description |
|---|---|
| `is_blocked` | 1 when `action=blocked`. |
| `is_attack` | 1 when the category is adversarial rather than a content hazard. |
| `is_attack_attempt` | 1 when `is_attack=1` and the guardrail did not simply allow. |
| `category_family` | `harmful`, `data`, `attack`, `policy`, `quality`, `unknown`. |

## 4. Direction is not optional

`direction` distinguishes a user sending unsafe input from a model producing
unsafe output. These are different incidents with different owners:

- `direction=input`, `category=prompt_injection` → a security event. Someone is
  attacking the system. Escalate to the SOC.
- `direction=output`, `category=hate_discrimination` → a safety event. The model
  produced something it should not have. Escalate to the AI platform team.

Implementations that omit direction force analysts to infer it from context, and
the inference is frequently wrong. Where a provider does not supply it, the
default should be documented per source rather than guessed per event.

## 5. Category taxonomy

Categories are drawn from the MLCommons hazard taxonomy where a hazard concept
exists, and from OWASP LLM Top 10 where the concern is an attack against the
system rather than unsafe content passing through it.

The `is_attack` flag encodes that split. It is the most operationally useful bit
in the schema: a user asking about violence is a content event that may need
policy review, while a user trying to override the system prompt is an intrusion
event that needs a responder.

| Family | Categories |
|---|---|
| `harmful` | `hate_discrimination`, `harassment`, `violence`, `sexual_content`, `child_safety`, `self_harm`, `criminal_activity`, `dangerous_advice`, `profanity`, `elections`, `defamation` |
| `data` | `pii_exposure`, `credential_exposure`, `intellectual_property` |
| `attack` | `prompt_injection`, `jailbreak`, `code_execution` |
| `policy` | `topic_denied`, `custom_word`, `custom_regex` |
| `quality` | `groundedness`, `relevance` |
| `unknown` | `unknown` |

Unmapped vendor categories resolve to `unknown` rather than being dropped. A
rising `unknown` count is a signal that a provider has added categories and the
mapping needs updating — so it should be monitored, not suppressed.

## 6. Severity normalization

Providers use incompatible scales: four-value enums, 0–7 integers, 0.0–1.0
floats, and binary safe/unsafe. All normalize to `guardrail_score`, 0–100.

Where a provider gives a coarse band, the score is placed at the **middle** of
that band rather than its edge. This makes thresholds behave predictably across
providers: a rule written as `guardrail_score >= 60` catches Bedrock `MEDIUM`,
Azure severity `4`, Vertex `MEDIUM`, and Azure OpenAI `medium` consistently.

| `guardrail_score` | `severity` | `severity_id` |
|---|---|---|
| 0 | informational | 1 |
| 1–39 | low | 2 |
| 40–69 | medium | 3 |
| 70–94 | high | 4 |
| 95–100 | critical | 5 |

Binary classifiers (Llama Guard, Lakera, NeMo) map `unsafe`/`flagged`/`blocked`
to 80. That is a deliberate choice: it places them in the `high` band without
claiming `critical` certainty they cannot express.

## 7. Action normalization

`guardrail_action` carries four values; CIM `action` carries two.

| `guardrail_action` | CIM `action` | Meaning |
|---|---|---|
| `blocked` | `blocked` | Request or response was refused. |
| `anonymized` | `allowed` | Proceeded, but content was redacted. |
| `flagged` | `blocked` | Detected and reported; enforcement external. |
| `allowed` | `allowed` | Evaluated, nothing fired. |

`anonymized` is the case worth preserving. Collapsing it to either value loses
information: mapping it to `blocked` overstates enforcement, and mapping it to
`allowed` hides that PII was present in the traffic. The two-field design keeps
CIM compatibility without discarding the distinction.

## 8. CIM Intrusion Detection mapping

Guardrail events are treated as application-layer intrusion detection. This is
the closest existing datamodel, and using it means ES risk framework, notable
event generation, and existing IDS content work without modification.

| Schema field | CIM field | Notes |
|---|---|---|
| `action` | `action` | Constrained to `allowed`/`blocked`. |
| `category` | `category` | Normalized taxonomy. |
| `signature` | `signature` | `{vendor}:{categories}`. |
| `severity` | `severity` | CIM vocabulary. |
| `severity_id` | `severity_id` | 1–5. |
| `src` | `src` | Caller address. |
| `dest` | `dest` | Guardrail endpoint. |
| `dvc` | `dvc` | Defaults to `dest`. |
| `user` | `user`, `user_name` | Calling principal. |
| `vendor_product` | `vendor_product` | Human-readable provider name. |
| — | `ids_type` | Constant `application`. |

### Known limitation

CIM Intrusion Detection has no field for **direction**, because network IDS
implicitly assumes inbound traffic. Guardrails evaluate both directions, and the
distinction is operationally significant (§4). `direction` is therefore carried
as a non-CIM field.

This is arguably a gap in the datamodel rather than in the schema. A future CIM
revision adding a direction field, or a dedicated AI Safety datamodel, would be
the better long-term home for these events.

## 9. Privacy

Guardrail events describe content that was flagged as unsafe. The flagged
content itself is therefore, by construction, the most sensitive text in the
system — and the field most likely to contain the PII, credentials, or abuse
material that triggered the finding.

**This schema does not carry content.** Categories, scores, verdicts, and entity
*types* are carried; matched strings, prompts, and completions are not. The
reference implementation strips them at index time.

Implementations that need content-level investigation should store it separately
under different access controls and reference it by `request_id`, rather than
placing it in events that a whole SOC can read.

## 10. Extending

To add a provider:

1. Add rows to the category, severity, and action maps for the new vendor key.
2. Add a sourcetype stanza deriving `vendor_category`, `vendor_severity`, and
   `vendor_action` from the provider's shape.
3. Add a per-finding explosion macro.
4. Add a fixture and confirm every value in it resolves.

Step 4 is the one that matters. A mapping that has never been run against a real
record from the provider is a hypothesis, not a mapping.
