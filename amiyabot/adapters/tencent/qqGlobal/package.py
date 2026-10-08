from amiyabot.adapters import BotAdapterProtocol
from amiyabot.adapters.tencent.qqGroup.package import (
    MESSAGE_CREATED,
    FULL_MESSAGE_CREATED,
    package_qq_group_message,
)
from amiyabot.adapters.tencent.qqGuild.package import package_qq_guild_message


async def package_qq_global_message(
    instance: BotAdapterProtocol,
    event: str,
    message: dict,
    is_reference: bool = False,
):
    if event in MESSAGE_CREATED or event in FULL_MESSAGE_CREATED:
        return await package_qq_group_message(instance, event, message, is_reference)

    return await package_qq_guild_message(instance, event, message, is_reference)
