import re

from dataclasses import dataclass
from amiyabot.util import remove_prefix_once
from amiyabot.builtin.message import Message, MessageMatch, Verify, Equal
from amiyabot.factory.factoryTyping import MessageHandlerItem, KeywordsType


@dataclass
class MessageHandlerItemImpl(MessageHandlerItem):
    def __check(self, data: Message, obj: KeywordsType) -> Verify:
        methods = {
            str: MessageMatch.check_str,
            Equal: MessageMatch.check_equal,
            re.Pattern: MessageMatch.check_reg,
        }
        t = type(obj)

        if t in methods:
            method = methods[t]
            check = Verify(*method(data, obj, self.level))
            if check:
                return check

        elif t is list:
            for item in obj:
                check = self.__check(data, item)
                if check:
                    return check

        return Verify(False)

    async def verify(self, data: Message):
        # 检查是否支持私信
        direct_only = self.direct_only or (self.group_config and self.group_config.direct_only)

        if data.is_direct:
            if not direct_only:
                if self.allow_direct is None:
                    if not self.group_config or not self.group_config.allow_direct:
                        return Verify(False)

                if self.allow_direct is False:
                    return Verify(False)
        else:
            if direct_only:
                return Verify(False)

        # 检查是否包含前缀触发词或被 @
        flag = False

        if self.check_prefix is None:
            need_check_prefix = self.group_config.check_prefix if self.group_config else True
        else:
            need_check_prefix = self.check_prefix

        if need_check_prefix:
            if data.is_at:
                flag = True
            else:
                prefix_keywords = need_check_prefix if isinstance(need_check_prefix, list) else self.prefix_keywords()

                if not prefix_keywords:
                    flag = True

                # 如果前缀校验通过，再次修正 Message 对象的属性值
                text, prefix = remove_prefix_once(data.text, prefix_keywords)
                if prefix:
                    flag = True
                    data.text_prefix = prefix
                    data.set_text(text, set_original=False)

        # 若不通过以上检查，且关键字不为全等句式（Equal）
        # 则允许当关键字为列表时，筛选列表内的全等句式继续执行校验，否则校验不通过
        if need_check_prefix and not flag and not isinstance(self.keywords, Equal):
            equal_filter = [n for n in self.keywords if isinstance(n, Equal)] if isinstance(self.keywords, list) else []
            if equal_filter:
                self.keywords = equal_filter
            else:
                return Verify(False)

        # 执行自定义校验并修正其返回值
        if self.custom_verify:
            result = await self.custom_verify(data)

            if isinstance(result, bool) or result is None:
                result = result, int(bool(result)), None

            elif isinstance(result, tuple):
                contrast = bool(result[0]), int(bool(result[0])), None
                result_len = len(result)
                result = (result + contrast[result_len:])[:3]

            return Verify(*result)

        return self.__check(data, self.keywords)

    async def action(self, data: Message):
        return await self.function(data)
