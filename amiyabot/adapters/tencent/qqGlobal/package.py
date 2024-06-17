from amiyabot.adapters import BotAdapterProtocol
from amiyabot.adapters.tencent.qqGroup.package import package_qq_group_message
from amiyabot.adapters.tencent.qqGuild.package import package_qq_guild_message


async def package_qq_global_message(
    instance: BotAdapterProtocol,
    event: str,
    message: dict,
    is_reference: bool = False,
):
    group_message_created = [
        'C2C_MESSAGE_CREATE',
        'GROUP_AT_MESSAGE_CREATE',
    ]

    if event in group_message_created:
        return await package_qq_group_message(instance, event, message, is_reference)

    return await package_qq_guild_message(instance, event, message, is_reference)
