# SPDX-License-Identifier: Apache-2.0
"""Experimental adapter to the pinned llama.cpp native GPT-OSS tool grammar."""
import json
import time
from openai_harmony import Message, Role, TextContent
from app.engine import LocalEngine, Cancelled, ModelFormatError, text_of_message
from app.prompting import compact_result
from app.sampling import native_temperature


def chat_history(history):
    """Translate complete Harmony transactions; private reasoning stays private."""
    result=[];reasoning=[];content=[];pending=[];serial=0
    for raw in history:
        message=Message.from_dict(raw);text=text_of_message(message)
        if message.author.role == Role.USER:
            result.append({'role':'user','content':text})
        elif message.author.role == Role.ASSISTANT:
            if message.recipient:
                if not message.recipient.startswith('functions.'):
                    raise ModelFormatError('Unsupported history recipient')
                json.loads(text)  # Never reinterpret or execute malformed history.
                serial+=1;identifier='call_'+str(serial);pending.append(identifier)
                result.append({'role':'assistant','content':'\n'.join(content) or None,
                    'reasoning_content':'\n'.join(reasoning),
                    'tool_calls':[{'id':identifier,'type':'function','function':{
                        'name':message.recipient.removeprefix('functions.'),'arguments':text}}]})
                reasoning=[];content=[]
            elif message.channel=='analysis':reasoning.append(text)
            else:content.append(text)
        elif message.author.role == Role.TOOL:
            if not pending:raise ModelFormatError('Tool result has no matching call')
            try:text=json.dumps(compact_result(json.loads(text)),ensure_ascii=False,separators=(',',':'))
            except ValueError:pass
            result.append({'role':'tool','tool_call_id':pending.pop(0),'content':text})
        else:raise ModelFormatError('Unexpected baseline history role')
    if pending:raise ModelFormatError('Tool history is incomplete')
    if content or reasoning:
        result.append({'role':'assistant','content':'\n'.join(content) or None,'reasoning_content':'\n'.join(reasoning)})
    return result


class ChatStream:
    def __init__(self):
        self.reasoning=[];self.content=[];self.calls={};self.finish=None;self.usage={};self.timings={}

    def accept(self,event):
        if event.get('error'):raise ModelFormatError('Local chat endpoint returned an error')
        if event.get('usage'):self.usage=event['usage']
        if event.get('timings'):self.timings=event['timings']
        for choice in event.get('choices',[]):
            if choice.get('index',0)!=0:raise ModelFormatError('Unexpected completion choice')
            delta=choice.get('delta',{})
            for field,target in (('reasoning_content',self.reasoning),('content',self.content)):
                if delta.get(field):target.append(delta[field])
            for call in delta.get('tool_calls',[]):
                index=call.get('index',0);saved=self.calls.setdefault(index,{'name':'','arguments':''})
                function=call.get('function',{})
                saved['name']+=function.get('name','');saved['arguments']+=function.get('arguments','')
            if choice.get('finish_reason') is not None:self.finish=choice['finish_reason']

    def replies(self,allowed):
        if self.finish=='length':return [],'MAX_TOKENS'
        if self.finish not in ('stop','tool_calls'):
            raise ModelFormatError('Stream ended without an accepted completion boundary')
        result=[]
        if self.reasoning:
            result.append(Message.from_role_and_content(Role.ASSISTANT,''.join(self.reasoning)).with_channel('analysis'))
        if self.calls:
            for index in sorted(self.calls):
                call=self.calls[index]
                try:arguments=json.loads(call['arguments'])
                except ValueError:raise ModelFormatError('Constrained tool arguments were not valid JSON') from None
                if call['name'] not in allowed or not isinstance(arguments,dict):
                    raise ModelFormatError('Unknown tool or non-object arguments')
                result.append(Message.from_role_and_content(Role.ASSISTANT,call['arguments']).with_channel('analysis').with_recipient('functions.'+call['name']))
        elif self.content:
            result.append(Message.from_role_and_content(Role.ASSISTANT,''.join(self.content)).with_channel('final'))
        else:raise ModelFormatError('Completion had neither tool call nor final')
        return result,'EOS'


class LlamaChatBaselineEngine(LocalEngine):
    def __init__(self,instructions,definitions):
        super().__init__();self.instructions=instructions;self.definitions=definitions

    def generate(self,history,cwd,emit,cancel,agent=True,max_tokens=2048,task_contract=None,reasoning_effort='medium'):
        with self.lock:
            self.last_activity=time.monotonic();self.load(cancel)
            if cancel.is_set():raise Cancelled()
            messages=[{'role':'system','content':self.instructions+'\nWorking folder: '+str(cwd)}]+chat_history(history)
            payload={'messages':messages,'tools':[{'type':'function','function':tool} for tool in self.definitions],
                'tool_choice':'auto','parallel_tool_calls':False,'reasoning_effort':reasoning_effort,
                'reasoning_format':'deepseek','max_tokens':-1,'stream':True,'stream_options':{'include_usage':True},
                'temperature':native_temperature(self.config),'top_p':1.0,'top_k':0,'min_p':0.0,
                'repeat_penalty':1.0,'cache_prompt':True}
            stream=ChatStream();started=time.monotonic();self.status='processing prompt'
            try:
                with self.session.client.stream('POST','/v1/chat/completions',json=payload) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if cancel.is_set():raise Cancelled()
                        if not line.startswith('data:'):continue
                        raw=line[5:].strip()
                        if raw=='[DONE]':break
                        stream.accept(json.loads(raw));self.status='generating'
                replies,reason=stream.replies({t['name'] for t in self.definitions})
            finally:
                self.last_activity=time.monotonic()
                if not cancel.is_set():self.status='ready'
            timings=stream.timings
            self.last_timing={'backend':'llama.cpp-native-chat-grammar','total_seconds':round(time.monotonic()-started,2),
                'prompt_tokens':stream.usage.get('prompt_tokens'), 'completion_tokens':stream.usage.get('completion_tokens'),
                'prefill_seconds':timings.get('prompt_ms',0)/1000,'decode_seconds':timings.get('predicted_ms',0)/1000,
                'reasoning_effort':reasoning_effort,'sampling_temperature':payload['temperature']}
            emit('metrics',self.last_timing)
            return replies,reason
