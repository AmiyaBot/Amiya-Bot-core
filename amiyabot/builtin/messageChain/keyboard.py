from typing import List, Union, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Permission:
    type: int = 2
    specify_role_ids: List[str] = field(default_factory=lambda: ['1', '2', '3'])
    specify_user_ids: List[str] = field(default_factory=lambda: [])


@dataclass
class RenderData:
    label: str = ''
    visited_label: str = ''
    style: int = 0


@dataclass
class Action:
    type: int = 2
    data: str = ''
    anchor: int = 0
    unsupport_tips: str = ''

    click_limit: int = 10

    reply: bool = False
    enter: bool = False
    at_bot_show_channel_list: bool = False

    permission: Permission = field(default_factory=Permission)


@dataclass
class Button:
    id: str
    render_data: RenderData = field(default_factory=RenderData)
    action: Action = field(default_factory=Action)


@dataclass
class Row:
    buttons: List[Button] = field(default_factory=list)

    def add_button(
        self,
        button: Union[str, Button],
        render_label: str,
        render_visited_label: str = '',
        render_style: int = 0,
        action_type: int = 2,
        action_data: str = '',
        action_anchor: int = 0,
        action_unsupport_tips: str = '',
        action_click_limit: int = 10,
        action_reply: bool = False,
        action_enter: bool = False,
        action_at_bot_show_channel_list: bool = False,
        permission_type: int = 2,
        permission_specify_role_ids: Optional[List[str]] = None,
        permission_specify_user_ids: Optional[List[str]] = None,
    ):
        if len(self.buttons) >= 5:
            raise OverflowError('Create up to 5 buttons per row')

        if isinstance(button, str):
            button = Button(button)

        button.render_data.label = render_label
        button.render_data.visited_label = render_visited_label or render_label
        button.render_data.style = render_style

        button.action.type = action_type
        button.action.data = action_data or render_label
        button.action.anchor = action_anchor
        button.action.unsupport_tips = action_unsupport_tips
        button.action.click_limit = action_click_limit
        button.action.reply = action_reply
        button.action.enter = action_enter
        button.action.at_bot_show_channel_list = action_at_bot_show_channel_list

        button.action.permission.type = permission_type
        button.action.permission.specify_role_ids = permission_specify_role_ids
        button.action.permission.specify_user_ids = permission_specify_user_ids

        self.buttons.append(button)

        return button


@dataclass
class InlineKeyboard:
    bot_appid: Union[str, int] = ''
    rows: List[Row] = field(default_factory=list)

    def add_row(self):
        if len(self.rows) >= 5:
            raise OverflowError('Create up to 5 rows')

        row = Row()
        self.rows.append(row)

        return row

    def dict(self):
        return asdict(self)
