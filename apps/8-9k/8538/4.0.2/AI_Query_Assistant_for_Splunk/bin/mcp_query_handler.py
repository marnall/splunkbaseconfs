"""
MCP Query Handler (v4.0.0)

Dual-path: routes between the new agentic pipeline (splunklib.ai Agent on
Python 3.13+) and the legacy v3 in-process pipeline (Python 3.9 fallback).

The user-facing /mcp_query REST endpoint is unchanged. Response shape gains
two optional fields when the agentic path is used:
    thread_id           — conversation thread for follow-up turns
    requires_clarification  — true when the agent thinks the question is ambiguous

Legacy fields (spl, explanation, risk_level, security_check, result) are
preserved verbatim so the existing frontend keeps working without changes
until appserver/static/mcp_query.js is updated in the UI task.
"""
import sys, os, json, time, uuid, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

# Bootstrap puts both legacy splunklib AND (if available) the agentic
# site-packages on sys.path. Idempotent.
from bootstrap import setup_paths, agentic_available
setup_paths()

import splunk.admin as admin
from mcp_base import MCPBaseHandler
from query_generator import QueryGenerator, AIGenerationError
from security_guardrail import SecurityGuardrail, SecurityBlockedError
from query_executor import QueryExecutor, QueryExecutionError
from integration_client import IntegrationClient, IntegrationError
from kv_store import KVStoreClient, KVStoreError
from validators import validate_string, ValidationError

logger = logging.getLogger(__name__)


class MCPQueryHandler(MCPBaseHandler):

    def setup(self):
        # v4: thread_id is the only new arg. Pass an existing thread_id to
        # continue a conversation; omit it to start a new thread (server
        # generates one).
        for arg in ('natural_language', 'context', 'output_mode', 'thread_id'):
            self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        pass

    def handleCreate(self, confInfo):
        # See v3 mcp_query_handler for the rationale of each error-handling
        # branch — that contract is preserved unchanged in v4.
        try:
            self._maybe_run_v2210_migration()
        except Exception:
            pass  # migration must never break query flow

        if not self._check_rate_limit():
            self._handle_error(
                confInfo, 'rate_limit',
                'Too many requests. Please wait before trying again.',
                as_exception=True,
            )
            return
        try:
            try:
                self._check_license()
            except admin.AdminManagerException as e:
                self._handle_error(confInfo, 'license_invalid', str(e), as_exception=True)
                return
            try:
                self._check_daily_query_limit()
            except admin.AdminManagerException as e:
                self._handle_error(confInfo, 'daily_limit', str(e), as_exception=True)
                return
            try:
                self._check_concurrent_query_limit()
            except admin.AdminManagerException as e:
                self._handle_error(confInfo, 'concurrent_limit', str(e), as_exception=True)
                return

            natural_language = self.callerArgs.data.get('natural_language', [None])[0]
            try:
                natural_language = validate_string(natural_language, 'natural_language', max_len=2000)
            except ValidationError as ve:
                raise admin.ArgValidationException(str(ve))
            context_str = self.callerArgs.data.get('context', [None])[0]
            try:
                context = json.loads(context_str) if context_str else None
            except (TypeError, ValueError):
                raise admin.ArgValidationException("context must be valid JSON")
            thread_id = self.callerArgs.data.get('thread_id', [None])[0] or None
            user = self.userName or 'unknown'

            config = self._get_config()
            integration_enabled = self._normalize_bool(config.get('integration', {}).get('enabled'))

            # Routing decision (in order of preference):
            #   1. integration (upstream MCP platform) — unchanged from v3
            #   2. agentic (splunklib.ai Agent) — when Python 3.13+ AND deps
            #      installed AND not explicitly opted out via config.ai.use_legacy
            #   3. legacy (v3 in-process pipeline) — fallback
            if integration_enabled:
                try:
                    result = self._query_via_platform(natural_language, user, config)
                    confInfo['result'].append('mode', 'integrated')
                except IntegrationError:
                    fallback = self._normalize_bool(
                        config.get('integration', {}).get('fallback_to_standalone', True)
                    )
                    if not fallback:
                        raise
                    result, mode = self._dispatch_standalone(
                        natural_language, context, user, thread_id, config
                    )
                    confInfo['result'].append('mode', f'{mode}_fallback')
            else:
                result, mode = self._dispatch_standalone(
                    natural_language, context, user, thread_id, config
                )
                confInfo['result'].append('mode', mode)

            for key, value in result.items():
                if isinstance(value, (dict, list)):
                    confInfo['result'].append(key, json.dumps(value))
                else:
                    confInfo['result'].append(key, str(value))

        except SecurityBlockedError as e:
            logger.warning(f"{self._log_prefix()} Security blocked: {e}")
            self._handle_error(confInfo, 'security_blocked', e, as_exception=True)
        except AIGenerationError as e:
            logger.exception(f"{self._log_prefix()} AI generation failed")
            self._handle_error(confInfo, 'ai_generation_failed', e)
        except QueryExecutionError as e:
            logger.exception(f"{self._log_prefix()} Query execution failed")
            self._handle_error(confInfo, 'query_execution_failed', e)
        except admin.ArgValidationException:
            raise
        except admin.AdminManagerException:
            raise
        except Exception as e:
            logger.exception(f"{self._log_prefix()} Unexpected error in query handler")
            self._handle_error(confInfo, 'unknown_error', e)

    # ---------------------------------------------------------------------
    # Dispatch + standalone paths
    # ---------------------------------------------------------------------

    def _dispatch_standalone(self, natural_language, context, user, thread_id, config):
        """Pick agentic vs legacy path and return (result_dict, mode_str)."""
        use_legacy = self._normalize_bool(config.get('ai', {}).get('use_legacy_path', False))
        if agentic_available() and not use_legacy:
            try:
                result = self._query_agentic(natural_language, context, user, thread_id, config)
                # Surface which sub-mode actually ran (single Agent vs 4-subagent
                # supervisor) so dashboards can split latency / cost by mode.
                mode = 'agentic-supervisor' if self._normalize_bool(
                    config.get('ai', {}).get('enable_supervisor', False)
                ) else 'agentic'
                return result, mode
            except ImportError as e:
                # Agentic path tried to load but a dep is missing — degrade
                # cleanly to legacy instead of 500'ing.
                logger.warning(
                    f"{self._log_prefix()} agentic path unavailable ({e}) — "
                    f"falling back to legacy path"
                )
        return self._query_standalone_legacy(natural_language, context, user, config), 'standalone'

    def _query_agentic(self, natural_language, context, user, thread_id, config):
        """v4 agentic pipeline.

        Steps:
          1. Resolve provider config from KV (same as legacy).
          2. Wrap as splunklib.ai Model via agentic.providers.build_model.
          3. Run an Agent with SplOutput structured output + middleware.
             - When ``ai.enable_supervisor=true`` the 4-subagent supervisor
               (planner / schema_resolver / spl_generator / auditor) is used
               in place of the single-Agent path.
          4. Execute the generated SPL via the existing QueryExecutor.
          5. (Supervisor + ``enable_explainer=true`` only) call the standalone
             explainer Agent to narrate the result rows in natural language.
          6. Persist conversation thread (Agent does this) + history record.
        """
        from agentic.agent_factory import (
            build_query_agent, build_supervisor_agent, build_explainer_agent,
        )
        from agentic.async_bridge import run_async
        from agentic.retry import call_with_retry
        from agentic.security import GuardrailBlockedError
        from agentic.schemas import QueryResponse, ExecutionResult
        from splunklib.ai.messages import HumanMessage  # type: ignore
        from usage_tracker import (
            increment_daily_query, increment_concurrent_query,
            decrement_concurrent_query, record_query_event,
        )

        # v4 feature flags (P0-#1 wire-up). Default OFF — single-agent path is
        # the cheap & reliable baseline; admins opt into the deeper pipeline.
        ai_cfg = config.get('ai', {}) or {}
        enable_supervisor = self._normalize_bool(ai_cfg.get('enable_supervisor', False))
        enable_explainer = self._normalize_bool(ai_cfg.get('enable_explainer', False))
        enable_remote_tools = self._normalize_bool(ai_cfg.get('enable_remote_tools', False))

        # Structured-log marker so a Splunk search like
        #   `index=_internal source=*splunkd.log* "event=agentic.start"`
        # can timeline every agentic invocation. We use key=value so Splunk's
        # KV_MODE extractor picks each field up without props.conf edits.
        _t_start = time.time()
        logger.info(
            f'{self._log_prefix()} event=agentic.start '
            f'mode={"supervisor" if enable_supervisor else "single"} '
            f'explainer={enable_explainer} remote_tools={enable_remote_tools} '
            f'user={user!r} thread_id={thread_id!r} nl_len={len(natural_language or "")}'
        )

        provider = self._get_default_provider()
        if not provider:
            raise AIGenerationError("No default AI provider configured.")

        service = self._get_splunk_service()
        executor = QueryExecutor(service, config.get('query', {}))

        # Quota counters charged AFTER provider resolution but BEFORE the LLM
        # call, matching v3 behaviour: a failed/blocked Agent run still
        # consumes a daily query, but a misconfigured provider doesn't.
        increment_daily_query(user)
        try: record_query_event(user)
        except Exception: pass
        increment_concurrent_query(user)

        try:
            extra_kw = tuple(
                k.strip() for k in str(
                    config.get('security', {}).get('dangerous_keywords', '')
                ).split(',') if k.strip()
            )
            max_hrs = int(config.get('security', {}).get('max_time_range_hours', 168))
            timeout = float(config.get('query', {}).get('timeout_seconds', 60))

            thread = thread_id or f"{user}:{uuid.uuid4().hex[:8]}"

            # Pick factory at runtime. Supervisor takes a few extra kwargs
            # (remote-tool toggle, allowlist) so we branch on which factory to
            # invoke instead of trying to massage one call site for both.
            async def run_agent():
                if enable_supervisor:
                    async with build_supervisor_agent(
                        provider_config=provider,
                        service=service,
                        user=user,
                        thread_id=thread,
                        max_time_range_hours=max_hrs,
                        extra_dangerous_keywords=extra_kw,
                        timeout_seconds=timeout,
                        enable_remote_tools=enable_remote_tools,
                    ) as agent:
                        return await agent.invoke_with_data(
                            instructions="Generate SPL for this question.",
                            data=natural_language,
                        )
                else:
                    async with build_query_agent(
                        provider_config=provider,
                        service=service,
                        user=user,
                        thread_id=thread,
                        max_time_range_hours=max_hrs,
                        extra_dangerous_keywords=extra_kw,
                        timeout_seconds=timeout,
                    ) as agent:
                        return await agent.invoke_with_data(
                            instructions="Generate SPL for this question.",
                            data=natural_language,
                        )

            # Bounded exponential-backoff retry around the LLM round-trip.
            # Providers occasionally hand back 429 / 5xx / gateway timeouts;
            # a single retry typically recovers without the user noticing.
            # `call_with_retry` re-invokes the coroutine factory on each
            # attempt — we wrap `run_agent` so the splunklib.ai Agent is
            # built fresh per attempt (its async context is single-use).
            #
            # Exception unwrapping: anyio TaskGroup (used by mcp / langchain)
            # bundles a single child exception in a BaseExceptionGroup. A
            # bare `except GuardrailBlockedError` won't catch
            # ExceptionGroup([GuardrailBlockedError]) — we manually peel the
            # group apart and re-raise the inner cause.
            _t_llm_start = time.time()
            try:
                ar = run_async(call_with_retry(run_agent, attempts=3))
            except BaseException as raw_exc:
                gb_inner = _find_in_excgroup(raw_exc, GuardrailBlockedError)
                if gb_inner is not None:
                    logger.info(
                        f'{self._log_prefix()} event=agentic.guardrail_blocked '
                        f'thread_id={thread!r} risk={gb_inner.risk_level!r} '
                        f'issues={list(gb_inner.issues)} '
                        f'elapsed_ms={int((time.time()-_t_llm_start)*1000)}'
                    )
                    raise SecurityBlockedError(
                        f"Query blocked: {gb_inner} "
                        f"(issues: {', '.join(gb_inner.issues)})"
                    )
                raise
            _t_llm_elapsed_ms = int((time.time() - _t_llm_start) * 1000)
            logger.info(
                f'{self._log_prefix()} event=agentic.llm_done '
                f'thread_id={thread!r} elapsed_ms={_t_llm_elapsed_ms}'
            )

            spl_out = ar.structured_output
            if spl_out is None:
                raise AIGenerationError("Agent returned no structured output")

            logger.info(
                f'{self._log_prefix()} event=agentic.spl_generated '
                f'thread_id={thread!r} risk={spl_out.risk_level!r} '
                f'requires_clarification={spl_out.requires_clarification} '
                f'spl_len={len(spl_out.spl or "")}'
            )

            if spl_out.requires_clarification:
                # Don't execute; return the clarification request to the UI.
                qr = QueryResponse(
                    query_id=str(uuid.uuid4()),
                    thread_id=thread,
                    spl_output=spl_out,
                    execution=ExecutionResult(success=False, error="awaiting_clarification"),
                    blocked_by_guardrail=False,
                )
                return self._flatten_query_response(qr)

            # Execute the SPL via existing executor (unchanged path).
            earliest = spl_out.time_range.earliest or '-24h'
            latest = spl_out.time_range.latest or 'now'
            try:
                exec_res = executor.execute(spl_out.spl, earliest, latest)
                exec_model = ExecutionResult(
                    success=True,
                    count=int(exec_res.get('count', 0)),
                    fields=list(exec_res.get('fields') or []),
                    data=list(exec_res.get('data') or []),
                    execution_time=float(exec_res.get('execution_time', 0.0)),
                )
            except QueryExecutionError as qe:
                exec_model = ExecutionResult(success=False, error=str(qe))

            # Explainer (supervisor + enable_explainer + non-empty rows).
            # Best-effort: a failure to narrate must NEVER fail the response,
            # so wrap the whole thing in try/except and log instead of raising.
            explainer_output = None
            if enable_supervisor and enable_explainer and exec_model.success and exec_model.count > 0:
                explainer_output = self._run_explainer_safe(
                    provider, service, natural_language, spl_out.spl,
                    exec_model, timeout,
                )

            # Persist to history KV (legacy-compatible row).
            qid = str(uuid.uuid4())
            history_saved = False
            history_error = ''
            try:
                kv = KVStoreClient(service, 'mcp_query_history')
                kv.insert({
                    'query_id': qid, 'user': user,
                    'natural_language': natural_language,
                    'spl': spl_out.spl,
                    'explanation': spl_out.explanation,
                    'risk_level': spl_out.risk_level,
                    'result_count': exec_model.count,
                    'execution_time': exec_model.execution_time,
                    'timestamp': int(time.time()),
                    'synced': False,
                    # v4-only fields (collection schema enforces ignoring unknowns
                    # if not declared, so these are added for forward-compat
                    # once collections.conf is extended in a later patch).
                    'thread_id': thread,
                })
                history_saved = True
            except Exception as e:
                history_error = str(e)
                logger.warning(
                    f'{self._log_prefix()} event=agentic.history_save_failed '
                    f'query_id={qid!r} error={e!r}'
                )

            qr = QueryResponse(
                query_id=qid,
                thread_id=thread,
                spl_output=spl_out,
                execution=exec_model,
                blocked_by_guardrail=False,
            )
            logger.info(
                f'{self._log_prefix()} event=agentic.done '
                f'thread_id={thread!r} query_id={qid!r} '
                f'exec_success={exec_model.success} rows={exec_model.count} '
                f'exec_ms={int(exec_model.execution_time * 1000)} '
                f'history_saved={history_saved} '
                f'explainer={explainer_output is not None} '
                f'total_ms={int((time.time() - _t_start) * 1000)}'
            )
            return self._flatten_query_response(
                qr, explainer_output=explainer_output,
                history_saved=history_saved, history_error=history_error,
            )
        finally:
            decrement_concurrent_query(user)

    def _run_explainer_safe(self, provider, service, nl, spl, exec_model, timeout):
        """Best-effort post-execution explainer narration.

        Returns an ``ExplainerOutput`` pydantic instance on success, or None
        when explainer is unavailable / errors out. A None return is silent;
        the calling code skips the ``explainer`` field on the response.

        We deliberately do NOT propagate any explainer error into the main
        query path — the SPL has already run, the rows are valid, and a
        failure to narrate them shouldn't drop the result on the floor.
        """
        from agentic.agent_factory import build_explainer_agent
        from agentic.async_bridge import run_async

        try:
            # Cap the result summary so the explainer doesn't choke on a huge
            # row dump. The agent gets row count + field list + first 5 rows.
            summary_rows = list(exec_model.data)[:5]
            result_summary = (
                f"{exec_model.count} rows. "
                f"Fields: {', '.join(exec_model.fields[:20])}. "
                f"Sample: {json.dumps(summary_rows, default=str)[:800]}"
            )

            async def run():
                async with build_explainer_agent(
                    provider_config=provider,
                    service=service,
                    timeout_seconds=min(float(timeout or 60.0), 30.0),
                ) as agent:
                    return await agent.invoke_with_data(
                        instructions="Explain the SPL results to the user.",
                        data={
                            "natural_language": nl,
                            "spl": spl,
                            "result_summary": result_summary,
                        },
                    )

            ar = run_async(run())
            return ar.structured_output
        except Exception as e:
            logger.warning(f"{self._log_prefix()} explainer failed (non-fatal): {e}")
            return None

    def _flatten_query_response(self, qr, explainer_output=None,
                                 history_saved=True, history_error=''):
        """Render a QueryResponse pydantic instance into the legacy flat dict
        that the existing frontend expects (plus a couple of new fields).

        :param explainer_output: optional ExplainerOutput pydantic instance.
            Only present when the supervisor path ran AND ai.enable_explainer
            is true AND the SPL returned at least one row.
        :param history_saved: whether the row was successfully persisted to
            mcp_query_history. Surfaced so the UI can show "history insert
            failed" without scraping splunkd.log.
        :param history_error: human-readable error string when history_saved
            is False; empty otherwise.
        """
        spl_out = qr.spl_output
        out = {
            'query_id': qr.query_id,
            'thread_id': qr.thread_id,
            'spl': spl_out.spl,
            'explanation': spl_out.explanation,
            'risk_level': spl_out.risk_level,
            'reasoning': spl_out.reasoning,
            'security_check': {
                'allowed': not qr.blocked_by_guardrail,
                'risk_level': spl_out.risk_level,
                'issues': [],
                'recommendation': '',
            },
            'time_range': spl_out.time_range.model_dump(),
            'expected_fields': spl_out.expected_fields,
            'requires_clarification': spl_out.requires_clarification,
            'clarification_question': spl_out.clarification_question,
            'result': qr.execution.model_dump(),
        }
        if explainer_output is not None:
            out['explainer'] = {
                'summary': explainer_output.summary,
                'key_findings': list(explainer_output.key_findings or []),
                'follow_up_suggestions': list(explainer_output.follow_up_suggestions or []),
            }
        out['history_saved'] = bool(history_saved)
        if not history_saved and history_error:
            out['history_error'] = history_error
        return out

    # ---------------------------------------------------------------------
    # Legacy v3 path — unchanged, runs on Python 3.9 fallback
    # ---------------------------------------------------------------------

    def _query_standalone_legacy(self, natural_language, context, user, config):
        from usage_tracker import increment_daily_query, increment_concurrent_query, decrement_concurrent_query, record_query_event

        provider = self._get_default_provider()
        if not provider:
            raise AIGenerationError("No default AI provider configured.")
        generator = QueryGenerator(provider)
        guardrail = SecurityGuardrail(config.get('security', {}))
        service = self._get_splunk_service()
        executor = QueryExecutor(service, config.get('query', {}))

        generated = generator.generate(natural_language, context)
        spl = generated['spl']
        security_check = guardrail.check(spl, natural_language)
        if not security_check['allowed']:
            raise SecurityBlockedError(f"Query blocked: {', '.join(security_check['issues'])}")

        time_range = generated.get('time_range', {})
        if not isinstance(time_range, dict):
            time_range = {}
        earliest = time_range.get('earliest', '-24h')
        latest = time_range.get('latest', 'now')

        increment_daily_query(user)
        try: record_query_event(user)
        except Exception: pass
        increment_concurrent_query(user)
        try:
            execution_result = executor.execute(spl, earliest, latest)

            query_id = str(uuid.uuid4())
            try:
                kv_client = KVStoreClient(service, 'mcp_query_history')
                kv_client.insert({
                    'query_id': query_id, 'user': user,
                    'natural_language': natural_language, 'spl': spl,
                    'explanation': generated['explanation'],
                    'risk_level': generated['risk_level'],
                    'result_count': execution_result['count'],
                    'execution_time': execution_result['execution_time'],
                    'timestamp': int(time.time()), 'synced': False
                })
            except Exception as e:
                logger.warning(f"{self._log_prefix()} Failed to save history: {e}")

            return {
                'query_id': query_id, 'spl': spl,
                'explanation': generated['explanation'],
                'risk_level': generated['risk_level'],
                'reasoning': generated.get('reasoning', ''),
                'security_check': security_check,
                'time_range': generated.get('time_range', {'earliest': earliest, 'latest': latest}),
                'result': execution_result
            }
        finally:
            decrement_concurrent_query(user)

    def _query_via_platform(self, natural_language, user, config):
        from usage_tracker import increment_daily_query, increment_concurrent_query, decrement_concurrent_query, record_query_event

        ic = IntegrationClient(config['integration'], session_key=self.getSessionKey())
        increment_daily_query(user)
        try: record_query_event(user)
        except Exception: pass
        increment_concurrent_query(user)
        try:
            result = ic.execute_query(natural_language, user)
            query_id = str(uuid.uuid4())
            try:
                service = self._get_splunk_service()
                kv_client = KVStoreClient(service, 'mcp_query_history')
                kv_client.insert({
                    'query_id': query_id, 'user': user,
                    'natural_language': natural_language, 'spl': result['spl'],
                    'explanation': result['explanation'],
                    'risk_level': result['risk_level'],
                    'result_count': result.get('result', {}).get('count', 0),
                    'execution_time': 0,
                    'timestamp': int(time.time()), 'synced': True
                })
            except Exception as e:
                logger.warning(f"{self._log_prefix()} Failed to save history: {e}")
            return {
                'query_id': query_id, 'spl': result['spl'],
                'explanation': result['explanation'],
                'risk_level': result['risk_level'],
                'result': result.get('result', {})
            }
        finally:
            decrement_concurrent_query(user)


def _find_in_excgroup(exc, target_cls):
    """Walk a Python 3.11+ ExceptionGroup (or any wrapped exception) looking
    for the first instance of ``target_cls``. Returns it, or None.

    Why we need this: anyio.TaskGroup (used by mcp + langchain async paths)
    aggregates child exceptions into a BaseExceptionGroup even when there is
    only ONE child. A bare ``except GuardrailBlockedError`` cannot catch
    ``BaseExceptionGroup([GuardrailBlockedError(...)])`` — Python's syntax
    for that is ``except* GuardrailBlockedError`` (PEP 654), but we still
    have to support older interpreters and we want a single code path that
    transparently handles both wrapped and unwrapped cases.

    Walks recursively into nested groups and follows __cause__/__context__
    chains so a langchain re-raise doesn't hide the cause.
    """
    if exc is None:
        return None
    if isinstance(exc, target_cls):
        return exc
    # ExceptionGroup / BaseExceptionGroup (Python 3.11+)
    exceptions = getattr(exc, "exceptions", None)
    if exceptions:
        for child in exceptions:
            found = _find_in_excgroup(child, target_cls)
            if found is not None:
                return found
    cause = getattr(exc, "__cause__", None)
    if cause is not None and cause is not exc:
        found = _find_in_excgroup(cause, target_cls)
        if found is not None:
            return found
    ctx = getattr(exc, "__context__", None)
    if ctx is not None and ctx is not exc:
        found = _find_in_excgroup(ctx, target_cls)
        if found is not None:
            return found
    return None


admin.init(MCPQueryHandler, admin.CONTEXT_APP_AND_USER)
