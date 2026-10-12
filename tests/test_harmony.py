import json
import unittest
from openai_harmony import (Author,Conversation,HarmonyEncodingName,Message,Role,TextContent,load_harmony_encoding)

class NativeHistoryTests(unittest.TestCase):
    def test_text_and_tool_history_survive_json_roundtrip(self):
        messages=[Message.from_role_and_content(Role.USER,'Please read my file.'),
            Message.from_role_and_content(Role.ASSISTANT,'{"path":"note.txt"}').with_channel('commentary').with_recipient('functions.read_file'),
            Message(author=Author.new(Role.TOOL,'functions.read_file'),content=[TextContent(text='the file contents')]).with_recipient('assistant')]
        restored=[Message.from_dict(json.loads(json.dumps(m.to_dict()))) for m in messages]
        encoding=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        self.assertEqual(encoding.render_conversation(Conversation.from_messages(messages)),encoding.render_conversation(Conversation.from_messages(restored)))
        rendered=encoding.decode(encoding.render_conversation(Conversation.from_messages(restored)))
        self.assertIn('the file contents',rendered)
        self.assertIn('functions.read_file',rendered)
