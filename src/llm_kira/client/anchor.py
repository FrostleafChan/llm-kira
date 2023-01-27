# -*- coding: utf-8 -*-
# @Time    : 1/23/23 11:18 PM
# @FileName: anchor.py
# @Software: PyCharm
# @Github    ：sudoskys
from typing import Union, Callable, List

from loguru import logger

# Tool

from . import Optimizer
from .enhance import Support
from .llms.base import LlmBaseParam
from .llms.openai import LlmBase
from .types import LlmReturn, LLMException
from ..utils.chat import Detect
from ..utils.data import MsgFlow
# 基于 Completion 上层
from .types import PromptItem, MemoryItem, Memory_Flow, ChatBotReturn
from .Optimizer import convert_msgflow_to_list

from .agent import Conversation


class Preset(object):
    """
    预设和角色
    """

    def __init__(self, profile: Conversation):
        self.profile = profile

    @staticmethod
    def add_tail(switch: bool = False, sentence: str = "", tail: str = ""):
        if switch:
            return f"{sentence}{tail}"
        else:
            return f"{sentence}"

    def character(self,
                  character: list = None,
                  lang: str = "ZH"
                  ) -> list:
        if character:
            return character
        lang = lang.upper()
        if lang == "ZH":
            return ["受过教育的", "聪明的",
                    "友好的", "可爱的",
                    "幽默地", "有趣地", "温柔地"]
        elif lang == "EN":
            return [
                "educated", "glamorous",
                "helpful", "girlish",
                "clever", "friendly",
                "cute", "talkative",
                "Humorously"
            ]
        elif lang == "JA":
            return ["教育された", "魅力的な", "丁寧な", "女性らしい", "賢い", "親切な", "可愛い", "喋っているような", "ユーモラスに", "興味深い",
                    "優しく"]
        else:
            return [
                "educated", "glamorous",
                "helpful", "girlish",
                "clever", "friendly",
                "cute", "talkative",
                "Humorously", "Interesting",
                "Tenderly"
            ]

    def role(self, role: str = "",
             restart_name: str = "",
             character: str = "",
             prompt_iscode: bool = False,
             lang: str = "ZH"
             ) -> str:
        if role:
            return role
        lang = lang.upper()
        role = ""
        if lang == "ZH":
            role = f"{restart_name} 是一个 {character} 的少女，聪明伶俐，经常帮我"
            role = self.add_tail(prompt_iscode, sentence=role, tail="是编程大师冠军,")
        elif lang == "EN":
            role = f"{restart_name} is a {character} girl, always help me"
            role = self.add_tail(prompt_iscode, sentence=role, tail="a Master Programmer Champion,")
        elif lang == "JA":
            role = f"{restart_name}は{character}の女の子です。 しばし手伝って"
            role = self.add_tail(prompt_iscode, sentence=role, tail="マスター プログラマー チャンピオンになる,")
        return f"{role} "

    def head(self,
             head: str = "",
             prompt_iscode: bool = False,
             lang: str = "ZH"
             ) -> str:
        if head:
            return head
        lang = lang.upper()
        head = ""
        start_name = self.profile.start_name
        restart_name = self.profile.restart_name
        if lang == "ZH":
            head = f"{start_name} 正在和 {restart_name} 聊天"
            head = self.add_tail(prompt_iscode, sentence=head, tail="提供编程指导,")
        elif lang == "EN":
            head = f"{start_name} chat with {restart_name} "
            head = self.add_tail(prompt_iscode, sentence=head, tail="Provide programming guidance,")
        elif lang == "JA":
            head = f"{start_name}と{restart_name}の会話 "
            head = self.add_tail(prompt_iscode, sentence=head, tail="プログラミング指導を提供する,")
        return f"{head} "


class PromptManager(object):
    def __init__(self,
                 profile: Conversation,
                 prompt_type: str = "chat",
                 template: str = None,
                 connect_words: str = "\n"
                 ):
        self.profile = profile
        self.__start_name = profile.start_name
        self.__restart_name = profile.restart_name
        self.__memory = []
        self.prompt_type = prompt_type
        self.template = template
        self.__connect_words = connect_words

    @property
    def restart_name(self):
        return self.__restart_name

    @property
    def start_name(self):
        return self.__start_name

    @property
    def type(self):
        return self.prompt_type

    def clean(self):
        self.__memory = []
        return True

    def override(self, item: List[PromptItem]):
        self.__memory = []
        for index in item:
            self.__memory.append(index)

    def insert(self, item: PromptItem):
        self.__memory.append(item)

    def run_template(self):
        return self.template

    def run(self,
            raw_list: bool = False
            ) -> Union[str, List[str]]:
        _result = []
        if not self.__memory:
            logger.warning("Your prompt seems empty!")
            self.__memory.append(PromptItem(start="Repeat", text="Warn,Your text seems empty!"))
        start = ""
        for item in self.__memory:
            item: PromptItem
            if item.start:
                start = f"{item.start}:"
            _result.append(f"{start}{item.text}")
        if raw_list:
            return _result
        return self.__connect_words.join(_result)


class MemoryManager(object):
    def __init__(self,
                 profile: Conversation,
                 ):
        self.profile = profile
        self._MsgFlow = MsgFlow(uid=self.profile.conversation_id)

    def reset_chat(self):
        # Forgets conversation
        return self._MsgFlow.forget()

    def read_memory(self, plain_text: bool = False, sign: bool = False) -> list:
        """
        读取记忆桶
        :param sign: 是否签名
        :param plain_text: 是否转化为列表
        """
        _result = self._MsgFlow.read()
        _result: List[Memory_Flow]
        if plain_text:
            _result = convert_msgflow_to_list(msg_list=_result, sign=sign)
        return _result

    def save_context(self, ask, reply, no_head: bool = True):
        """
        回复填充进消息桶
        """
        # 新建对话
        _msg = MemoryItem(**{"weight": [],
                             "ask": f"{self.profile.restart_name}:{ask}",
                             "reply": f"{self.profile.start_name}:{reply}"})
        if no_head:
            _msg = MemoryItem(**{"weight": [], "ask": f"{ask}", "reply": f"{reply}"})
        # 存储对话
        self._MsgFlow.saveMsg(msg=_msg)
        return _msg


class ChatBot(object):
    def __init__(self,
                 profile: Conversation,
                 memory_manger: MemoryManager,
                 optimizer: Optimizer = Optimizer.SinglePoint,
                 llm_model: LlmBase = None
                 ):
        """
        类型类型，所需的依赖元素
        """
        self.profile = profile
        self.prompt = None
        self.memory_manger = memory_manger
        self.optimizer = optimizer
        if optimizer is None:
            self.optimizer = Optimizer.SinglePoint
        self.llm = llm_model
        if llm_model is None:
            raise LLMException("Whats your llm model?")

    async def predict(self,
                      prompt: PromptManager,
                      increase: Union[str, Support] = "",
                      predict_tokens: int = 100,
                      parse_reply: Callable[[list], str] = None,
                      llm_param: LlmBaseParam = None,
                      ) -> ChatBotReturn:
        self.prompt = prompt
        if parse_reply:
            self.llm.parse_reply = parse_reply

        predict_tokens += self.llm.tokenizer(self.profile.restart_name)
        if predict_tokens > self.llm.get_token_limit():
            raise LLMException("Why your predict token > set token limit?")

        prompt_text: str = self.prompt.run(raw_list=False)
        # prompt 前向注入
        prompt_raw: list = self.prompt.run(raw_list=True)
        __extra_memory = []
        for item in prompt_raw:
            index = round(len(item) / 3) if round(len(item) / 3) > 3 else 10
            if ":" in item[:index]:
                __extra_memory.append(item)
            else:
                self.memory_manger.save_context(ask=item,
                                                reply=item,
                                                no_head=True)
            if len(__extra_memory) == 2:
                self.memory_manger.save_context(ask=__extra_memory[0],
                                                reply=__extra_memory[1],
                                                no_head=True)
                __extra_memory.clear()
        # Prompt Info
        prompt_lang: str = Detect.get_text_language(sentence=prompt_text)
        prompt_iscode: bool = Detect.isCode(sentence=prompt_text)
        prompt_preset = Preset(self.profile)
        # Template
        template: str = self.prompt.run_template()
        # Preset LLM Head
        if template is None:
            __template = []
            # Head
            head = prompt_preset.head(prompt_iscode=prompt_iscode,
                                      lang=prompt_lang)
            __template.append(head)
            # Character
            character = prompt_preset.character(lang=prompt_lang)
            _role = prompt_preset.role(restart_name=self.profile.restart_name,
                                       character=",".join(character),
                                       prompt_iscode=prompt_iscode,
                                       lang=prompt_lang)
            role = f"\n{_role}."
            __template.append(role)
            template = ''.join(__template)
        # Memory Read
        _prompt_memory = self.memory_manger.read_memory(plain_text=False)

        # Advance Template
        _prompt_head = []
        _prompt_body = []
        _prompt_foot = []
        _prompt_foot.extend([f"{prompt_text}"])
        # Enhance
        if isinstance(increase, str):
            _appendix = increase
        else:
            _appendix = await increase.run()
        _prompt_head.append(template)
        _prompt_head.append(_appendix)
        # Cut Size
        _body_token = int(
            predict_tokens +
            # len(_prompt_memory) +
            self.llm.tokenizer(''.join(_prompt_head)) +
            self.llm.tokenizer(''.join(_prompt_foot)) +
            1  # \n
        )

        # Run Optimizer
        _prompt_optimized = self.optimizer(
            prompt=prompt_text,
            memory=_prompt_memory,
            extra_token=_body_token,
            token_limit=self.llm.get_token_limit(),
            tokenizer=self.llm.tokenizer,
        ).run()
        _prompt_body.extend(_prompt_optimized)

        # Resize
        _llm_result_limit = self.llm.get_token_limit() - predict_tokens
        _prompt = self.llm.resize_context(head=_prompt_head,
                                          body=_prompt_body,
                                          foot=_prompt_foot,
                                          token=_llm_result_limit)

        # Clean
        _prompt_body = [item for item in _prompt_body if item]

        # Stick Them
        _prompt = _prompt + f"\n{self.profile.restart_name}:"
        if not prompt_iscode:
            _prompt = _prompt.replace("\n\n", "\n")

        # ODO
        # logger.warning(_prompt)

        # Get
        llm_result = await self.llm.run(prompt=_prompt, predict_tokens=predict_tokens, llm_param=llm_param)
        llm_result: LlmReturn

        # Parse Result
        self.memory_manger.save_context(ask=prompt_text,
                                        reply=f"{self.profile.restart_name}:{self.llm.parse_reply(llm_result.reply)}",
                                        no_head=True)
        return ChatBotReturn(conversation_id=f"{self.profile.conversation_id}",
                             llm=llm_result,
                             ask=prompt_text,
                             reply=self.llm.parse_reply(llm_result.reply))
