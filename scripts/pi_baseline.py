# SPDX-License-Identifier: Apache-2.0
"""Local-only Pi configuration and public event filtering for native comparisons."""
import os
from pathlib import Path

FLAGS = ['--offline', '--no-context-files', '--no-extensions', '--no-mcp',
         '--no-skills', '--no-prompt-templates', '--no-themes', '--no-approve']


def child_environment(root, private, key):
    # Deliberately do not inherit cloud credentials, proxy settings or shell startup hooks.
    env = {k: os.environ[k] for k in ('HOME', 'USER', 'LANG', 'LC_ALL', 'TZ') if k in os.environ}
    env.update(PATH=str(root / '.venv/bin') + ':/usr/local/bin:/usr/bin:/bin',
               PI_CODING_AGENT_DIR=str(private), PI_OFFLINE='1', PI_TELEMETRY='0',
               TINY_DANCER_TEST_API_KEY=key, TMPDIR=str(private / 'tmp'),
               NO_COLOR='1', PYTHONDONTWRITEBYTECODE='1')
    return env


def models_config(base_url):
    from urllib.parse import urlsplit
    url = urlsplit(base_url)
    if url.scheme != 'http' or url.hostname != '127.0.0.1' or url.username or url.password:
        raise ValueError('Comparison requires an authenticated loopback model endpoint')
    return {'providers': {'tiny-local': {'baseUrl': base_url.rstrip('/') + '/v1',
        'api': 'openai-completions', 'apiKey': '$TINY_DANCER_TEST_API_KEY',
        'models': [{'id': 'gpt-oss-20b', 'name': 'Local original GPT-OSS-20B',
            'reasoning': True, 'input': ['text'], 'contextWindow': 32768, 'maxTokens': 32768,
            'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
            'thinkingLevelMap': {'low': 'low', 'medium': 'medium', 'high': 'high'},
            'compat': {'supportsStore': False, 'supportsDeveloperRole': False,
                'supportsReasoningEffort': True, 'supportsUsageInStreaming': True,
                'maxTokensField': 'max_tokens', 'thinkingFormat': 'openai',
                'requiresThinkingAsText': False},
            'samplingParams': {'temperature': 1.0, 'top_p': 1.0, 'top_k': 0, 'min_p': 0.0,
                'repeat_penalty': 1.0, 'cache_prompt': True, 'parallel_tool_calls': False,
                'reasoning_format': 'deepseek'}}]}}}


def settings_config(effort):
    return {'defaultProvider': 'tiny-local', 'defaultModel': 'gpt-oss-20b',
        'defaultThinkingLevel': effort, 'enabledModels': ['tiny-local/gpt-oss-20b'],
        'enableInstallTelemetry': False, 'cacheWarming': 'off',
        'compaction': {'enabled': True, 'reserveTokens': 8192, 'keepRecentTokens': 8192},
        # Pi passes this value directly to the OpenAI-compatible SDK: zero means
        # immediate timeout there, despite zero disabling Pi's HTTP idle timer.
        # Use the maximum safe JS timer (24.8 days per request); the observer's
        # actual inactivity/Stop/RAM guards remain, with no aggregate task limit.
        'httpIdleTimeoutMs': 0, 'retry': {'enabled': True, 'maxRetries': 3,
            'provider': {'timeoutMs': 2147483647, 'maxRetries': 0}}, 'shellPath': '/bin/bash'}


def public_event(event):
    """Whitelist actual tools and numeric metadata; never return assistant prose."""
    kind = event.get('type')
    if kind == 'tool_execution_start':
        return {'type': kind, 'name': event.get('toolName'), 'args': event.get('args'),
                'id': event.get('toolCallId')}
    if kind == 'tool_execution_end':
        result = event.get('result') or {}
        text = '\n'.join(c.get('text', '') for c in result.get('content', []) if c.get('type') == 'text')
        return {'type': kind, 'name': event.get('toolName'), 'id': event.get('toolCallId'),
                'is_error': bool(event.get('isError')), 'duration_ms': event.get('durationMs'),
                'result_text': text[-16000:]}
    if kind == 'message_end' and event.get('message', {}).get('role') == 'assistant':
        message = event['message']
        usage = {k: v for k, v in message.get('usage', {}).items() if isinstance(v, (int, float))}
        return {'type': 'inference', 'stop_reason': message.get('stopReason'), 'usage': usage,
            'private_characters': sum(len(c.get('thinking', '')) for c in message.get('content', [])
                                      if c.get('type') == 'thinking')}
    if kind in ('agent_start', 'agent_end', 'turn_start', 'turn_end'):
        return {'type': kind}
    if kind in ('auto_compaction_start', 'auto_compaction_end', 'auto_retry_start', 'auto_retry_end'):
        return {'type': kind}  # summaries/retry bodies may contain private provider text
    return None
