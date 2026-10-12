# SPDX-License-Identifier: Apache-2.0
"""Continue Auto work to a real response boundary or the physical context limit."""


def continue_reply(session,prompt_length,produced,reason,chunk_tokens,on_token,*,temperature=0.0):
    if type(chunk_tokens) is not int or chunk_tokens<=0:
        raise ValueError('Native continuation requires a positive integer chunk size')
    timings=[dict(session.last_timing)]
    produced=list(produced)
    ceiling=session.ctx-prompt_length-1
    while reason=='MAX_TOKENS' and len(produced)<ceiling:
        allowance=min(chunk_tokens,ceiling-len(produced))
        tokens,reason,_=session.turn([],allowance,prompt_length+len(produced),on_token,temperature=temperature)
        if not tokens or len(tokens)>allowance:
            raise RuntimeError('Native continuation did not honor its bounded token receipt')
        produced.extend(tokens);timings.append(dict(session.last_timing))
    if reason=='MAX_TOKENS' and len(produced)>=ceiling:
        reason='CONTEXT_FULL'
    timing=dict(timings[-1])
    for phase in ('prefill','decode'):
        seconds=sum(float(item.get(phase+'_seconds',0)) for item in timings)
        tokens=sum(int(item.get(phase+'_tokens',0)) for item in timings)
        timing.update({phase+'_seconds':seconds,phase+'_tokens':tokens,phase+'_tokens_per_s':tokens/seconds if seconds else None})
    timing['native_reply_chunks']=len(timings)
    timing['native_reply_context_capacity']=ceiling
    return produced,reason,timing
