# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/04/27 02:09:28
# @modified 2019/05/01 14:50:25

import os
import re
import math
import time
import web
import xconfig
import xutils
import xauth
import xmanager
import xtables
import xtemplate
from xtemplate import BasePlugin
from xutils import dbutil

HTML = """
<!-- Html -->

<div class="card">
    xnote从2.3版本开始，数据库采用leveldb，不再使用sqlite，此工具用于把sqlite数据库数据迁移到leveldb

    <div>
        <a class="btn" href="?action=note_full">迁移笔记主表</a>
        <a class="btn" href="?action=message">迁移提醒</a>
        <a class="btn" href="?action=build_index">构建索引</a>
    </div>

    <div class="top-offset-1">
        {{result}}
        {% if cost > 0 %}
            耗时: {{cost}} ms
        {% end %}
    </div>
</div>
"""

class MigrateHandler(BasePlugin):

    title = "数据迁移"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network}
    category = None
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 0
        result = ""

        action = xutils.get_argument("action")
        t1 = time.time()

        if action == "note_full":
            result = migrate_note_full()
        if action == "note_history":
            result = migrate_note_history()
        if action == "build_index":
            result = build_index()
        if action == "message":
            result = migrate_message()

        cost = int((time.time() - t1) * 1000)
        self.writetemplate(HTML, result = result, cost = cost)

def migrate_note_recent():
    recent_list = dbutil.prefix_iter("z:note.recent", include_key = True)
    for key, item in recent_list:
        dbutil.delete(key)
    db = xtables.get_note_table()
    for item in dbutil.prefix_iter("note_tiny"):
        if item.type != "group":
            dbutil.zadd("z:note.recent:%s" % item.creator, "%02d:%s" % (item.priority, item.mtime), item.id)
        if item.is_public:
            dbutil.zadd("z:note.recent:public", "%02d:%s" % (item.priority, item.mtime), item.id)
    return "迁移完成!"

def migrate_note_history():
    # sqlite to kv
    db = xtables.get_note_history_table()
    for item in db.select():
        dbutil.put("note_history:%s:%s" % (item.note_id, item.version), item)

    # old_key to new_key
    for item in dbutil.prefix_iter("note.history"):
        # 这里leveldb第一版没有note_id，而是id字段
        old_key   = "note.history:%s:%s" % (item.id, item.version)
        new_key   = "note_history:%s:%s" % (item.id, item.version)
        new_value = dbutil.get(new_key)
        if new_value and (new_value.mtime is None or item.mtime > new_value.mtime):
            dbutil.put(new_key, item)
            dbutil.delete(old_key)

        if new_value is None:
            dbutil.put(new_key, item)
            dbutil.delete(old_key)
    return "迁移完成!"

def build_full_note(note, db):
    id = note.id
    result = db.select_first(where=dict(id=id))
    if result is None:
        return

    content = result.get("content", "")
    data = result.get("data", "")
    if content != "":
        note.content = content
    if data != "":
        note.data = data

def migrate_note_full():
    # sqlite to leveldb
    db = xtables.get_note_table()
    content_db = xtables.get_note_content_table()
    for item in db.select():
        ldb_value = dbutil.get("note_full:%s" % item.id)
        # 如果存在需要比较修改时间
        if ldb_value and item.mtime >= ldb_value.mtime:
            build_full_note(item, content_db)
            dbutil.put("note_full:%s" % item.id, item)
        
        if ldb_value is None:
            build_full_note(item, content_db)
            dbutil.put("note_full:%s" % item.id, item)
    # old key to new key
    for item in dbutil.prefix_iter("note.full:"):
        new_key   = "note_full:%s" % item.id
        new_value = dbutil.get(new_key)
        if new_value and item.mtime >= new_value.mtime:
            dbutil.put(new_key, item)
        
        if new_value is None:
            dbutil.put(new_key, item)

    return "迁移完成!"


def build_index():
    # 先删除老的索引
    for key, value in dbutil.prefix_iter("note_tiny:", include_key = True):
        dbutil.delete(key)

    # old key to new key
    for item in dbutil.prefix_iter("note_full:"):
        key = "note_tiny:%s:%020d" % (item.creator, int(item.id))
        del item.content
        del item.data
        dbutil.put(key, item)

    migrate_note_recent()
    return "迁移完成!"

def migrate_message():
    db = xtables.get_message_table()
    for item in db.select():
        try:
            unix_timestamp = xutils.parse_time(item.ctime)
        except:
            unix_timestamp = xutils.parse_time(item.ctime, "%Y-%m-%d")
        timestamp = "%020d" % (unix_timestamp * 1000)
        key = "message:%s:%s" % (item.user, timestamp)

        item["old_id"] = item.id
        item["id"] = key
        
        ldb_value = dbutil.get(key)
        put_to_db = False
        if ldb_value and item.mtime >= ldb_value.mtime:
            put_to_db = True
        if ldb_value is None:
            put_to_db = True

        if put_to_db:
            dbutil.put(key, item)
    return "迁移完成!"

SCAN_HTML = """
<div class="card">
    <table class="table">
        {% for key, value in result %}
            <tr>
                <td style="width:20%">{{key}}</td>
                <td style="width:80%">{{value}}</td>
            </tr>
        {% end %}
    </table>
    <a href="?key_from={{key}}">下一页</a>
</div>
"""

class DbScanHandler(BasePlugin):

    title = "数据库扫描"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network}
    category = None

    placeholder = "主键"
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 1
        result = []
        reverse = xutils.get_argument("reverse") == "true"
        key_from = xutils.get_argument("key_from", None)

        def func(key, value):
            if input in key:
                result.append((key, value))
                if len(result) > 30:
                    return False
            return True

        dbutil.scan(key_from = key_from, func = func, reverse = reverse)
        self.writetemplate(SCAN_HTML, result = result)


xurls = (
    "/system/db_migrate", MigrateHandler,
    "/system/db_scan", DbScanHandler,
)