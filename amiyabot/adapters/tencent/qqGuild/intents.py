class PublicIntents:
    GUILDS = 1 << 0
    GUILD_MEMBERS = 1 << 1
    GUILD_MESSAGE_REACTIONS = 1 << 10
    DIRECT_MESSAGE = 1 << 12
    INTERACTION = 1 << 26
    MESSAGE_AUDIT = 1 << 27
    AUDIO_ACTION = 1 << 29
    PUBLIC_GUILD_MESSAGES = 1 << 30

    @classmethod
    def public_intents(cls, private: bool = False):
        intent = 0
        intent |= cls.GUILDS
        intent |= cls.GUILD_MEMBERS
        intent |= cls.GUILD_MESSAGE_REACTIONS
        intent |= cls.DIRECT_MESSAGE
        intent |= cls.INTERACTION
        intent |= cls.MESSAGE_AUDIT
        intent |= cls.AUDIO_ACTION

        if not private:
            intent |= cls.PUBLIC_GUILD_MESSAGES

        return intent

    @classmethod
    def get_all_intents(cls):
        return cls.public_intents()


class PrivateIntents(PublicIntents):
    GUILD_MESSAGES = 1 << 9
    FORUMS_EVENT = 1 << 28

    @classmethod
    def get_all_intents(cls):
        intent = cls.public_intents(private=True)
        intent |= cls.GUILD_MESSAGES
        intent |= cls.FORUMS_EVENT

        return intent


class Intents:
    def __init__(self, private: bool):
        self.intents = PrivateIntents if private else PublicIntents


"""
GUILDS (1 << 0)
  - GUILD_CREATE   // 当机器人加入新guild时
  - GUILD_UPDATE   // 当guild资料发生变更时
  - GUILD_DELETE   // 当机器人退出guild时
  - CHANNEL_CREATE // 当channel被创建时
  - CHANNEL_UPDATE // 当channel被更新时
  - CHANNEL_DELETE // 当channel被删除时

GUILD_MEMBERS (1 << 1)
  - GUILD_MEMBER_ADD    // 当成员加入时
  - GUILD_MEMBER_UPDATE // 当成员资料变更时
  - GUILD_MEMBER_REMOVE // 当成员被移除时

GUILD_MESSAGES (1 << 9) // 消息事件，仅 *私域* 机器人能够设置此 intents。
  - MESSAGE_CREATE      // 发送消息事件，代表频道内的全部消息，而不只是 at 机器人的消息。内容与 AT_MESSAGE_CREATE 相同
  - MESSAGE_DELETE      // 删除（撤回）消息事件

GUILD_MESSAGE_REACTIONS (1 << 10)
  - MESSAGE_REACTION_ADD    // 为消息添加表情表态
  - MESSAGE_REACTION_REMOVE // 为消息删除表情表态

DIRECT_MESSAGE (1 << 12)
  - DIRECT_MESSAGE_CREATE // 当收到用户发给机器人的私信消息时
  - DIRECT_MESSAGE_DELETE // 删除（撤回）消息事件

INTERACTION (1 << 26)
  - INTERACTION_CREATE // 互动事件创建时

MESSAGE_AUDIT (1 << 27)
- MESSAGE_AUDIT_PASS   // 消息审核通过
- MESSAGE_AUDIT_REJECT // 消息审核不通过

FORUMS_EVENT (1 << 28)         // 论坛事件，仅 *私域* 机器人能够设置此 intents。
  - FORUM_THREAD_CREATE        // 当用户创建主题时
  - FORUM_THREAD_UPDATE        // 当用户更新主题时
  - FORUM_THREAD_DELETE        // 当用户删除主题时
  - FORUM_POST_CREATE          // 当用户创建帖子时
  - FORUM_POST_DELETE          // 当用户删除帖子时
  - FORUM_REPLY_CREATE         // 当用户回复评论时
  - FORUM_REPLY_DELETE         // 当用户删除评论时
  - FORUM_PUBLISH_AUDIT_RESULT // 当用户发表审核通过时

AUDIO_ACTION (1 << 29)
  - AUDIO_START   // 音频开始播放时
  - AUDIO_FINISH  // 音频播放结束时
  - AUDIO_ON_MIC  // 上麦时
  - AUDIO_OFF_MIC // 下麦时

PUBLIC_GUILD_MESSAGES (1 << 30) // 消息事件，此为公域的消息事件
  - AT_MESSAGE_CREATE           // 当收到@机器人的消息时
  - PUBLIC_MESSAGE_DELETE       // 当频道的消息被删除时

"""
