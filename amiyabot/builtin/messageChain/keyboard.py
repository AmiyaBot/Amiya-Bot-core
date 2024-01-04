from typing import List, Union, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Permission:
    type: int = 1
    specify_role_ids: List[str] = field(default_factory=lambda: ['1', '2', '3'])
    specify_user_ids: List[str] = field(default_factory=lambda: [])


@dataclass
class RenderData:
    label: str = ''
    visited_label: str = ''


@dataclass
class Action:
    type: int = 1
    data: str = ''
    unsupport_tips: str = ''

    reply: bool = False
    enter: bool = False
    anchor: bool = False
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
        label: str,
        visited_label: Optional[str] = None,
        action_type: int = 1,
        action_data: str = '',
    ):
        if len(self.buttons) >= 5:
            raise OverflowError('Create up to 5 buttons per row')

        if isinstance(button, str):
            button = Button(button)

        button.render_data.label = label
        button.render_data.visited_label = visited_label or label
        button.action.type = action_type
        button.action.data = action_data or button.id

        self.buttons.append(button)

        return button


@dataclass
class InlineKeyboard:
    bot_appid: int
    rows: List[Row] = field(default_factory=list)

    def add_row(self):
        if len(self.rows) >= 5:
            raise OverflowError('Create up to 5 rows')

        row = Row()
        self.rows.append(row)

        return row

    def dict(self):
        return asdict(self)
