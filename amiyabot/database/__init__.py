import peewee
import pymysql

from abc import ABC
from typing import List, Any, Optional
from dataclasses import dataclass
from playhouse.migrate import *
from playhouse.shortcuts import ReconnectMixin, model_to_dict
from amiyabot.util import create_dir, pascal_case_to_snake_case


@dataclass
class MysqlConfig:
    host: str = '127.0.0.1'
    port: int = 3306
    user: str = 'root'
    password: str = ''

    def dict(self):
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
        }


class ReconnectMySQLDatabase(ReconnectMixin, MySQLDatabase, ABC):
    ...


class ModelClass(Model):
    @classmethod
    def batch_insert(cls, rows: List[dict], chunk_size: int = 200):
        if len(rows) > chunk_size:
            for batch in chunked(rows, chunk_size):
                cls.insert_many(batch).execute()
        else:
            cls.insert_many(rows).execute()

    @classmethod
    def insert_or_update(
        cls,
        insert: dict,
        update: Optional[dict] = None,
        conflict_target: Optional[list] = None,
        preserve: Optional[list] = None,
    ):
        conflict = {'update': update, 'preserve': preserve}
        if isinstance(cls._meta.database, ReconnectMySQLDatabase):
            conflict['conflict_target'] = conflict_target

        cls.insert(**insert).on_conflict(**conflict).execute()


class DatabaseConfigError(Exception):
    def __init__(self, value: Any):
        self.value = value

    def __str__(self):
        return f'Expected MysqlConfig instance, got {self.value} instead'


def table(cls: ModelClass) -> Any:
    database: Database = cls._meta.database
    migrator: SchemaMigrator = SchemaMigrator.from_database(cls._meta.database)

    table_name = pascal_case_to_snake_case(cls.__name__)

    cls._meta.table_name = table_name
    cls.create_table()

    description = database.execute_sql(f'select * from `{table_name}` limit 1').description

    model_columns = [f for f, n in cls.__dict__.items() if type(n) in [peewee.FieldAccessor, peewee.ForeignKeyAccessor]]
    table_columns = [n[0] for n in description]

    migrate_list = []

    # 取 AB 差集增加字段
    for f in set(model_columns) - set(table_columns):
        migrate_list.append(migrator.add_column(table_name, f, getattr(cls, f)))

    # 取 BA 差集删除字段
    for f in set(table_columns) - set(model_columns):
        migrate_list.append(migrator.drop_column(table_name, f))

    if migrate_list:
        migrate(*tuple(migrate_list))

    return cls


def connect_database(database: str, is_mysql: bool = False, config: Optional[MysqlConfig] = None):
    if is_mysql:
        if not isinstance(config, MysqlConfig):
            raise DatabaseConfigError(config)

        conn = pymysql.connect(**config.dict(), charset='utf8')
        cursor = conn.cursor()
        cursor.execute(f'CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8;')
        cursor.close()
        conn.close()

        return ReconnectMySQLDatabase(database, **config.dict())

    create_dir(database, is_file=True)
    return SqliteDatabase(database, pragmas={'timeout': 30})


def convert_model(model, select_model: Optional[peewee.Select] = None) -> dict:
    data = {**model_to_dict(model)}
    if select_model:
        for field in select_model._returning:
            if field.name not in data:
                data[field.name] = getattr(model, field.name)

    return data


def query_to_list(query, select_model: Optional[peewee.Select] = None) -> List[dict]:
    return [convert_model(item, select_model) for item in query]


def select_for_paginate(select: peewee.ModelSelect, page: int, page_size: int):
    return {
        'list': query_to_list(
            select.objects().paginate(page=page, paginate_by=page_size),
            select_model=select,
        ),
        'total': select.count(),
    }
