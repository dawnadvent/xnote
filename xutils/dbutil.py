# encoding=utf-8
import os
import time
import json

try:
    import sqlite3
except ImportError:
    sqlite3 = None

try:
    import leveldb
except ImportError:
    leveldb = None

from xconfig import Storage

###########################################################
# @desc db utilties
# @author xupingmao
# @email 578749341@qq.com
# @since 2015-11-02 20:09:44
# @modified 2019/05/01 10:17:05
###########################################################

def search_escape(text):
    if not (isinstance(text, str) or isinstance(text, unicode)):
        return text
    text = text.replace('/', '//')
    text = text.replace("'", '\'\'')
    text = text.replace('[', '/[')
    text = text.replace(']', '/]')
    #text = text.replace('%', '/%')
    #text = text.replace('&', '/&')
    #text = text.replace('_', '/_')
    text = text.replace('(', '/(')
    text = text.replace(')', '/)')
    return "'%" + text + "%'"

def to_sqlite_obj(text):
    if text is None:
        return "NULL"
    if not (isinstance(text, str)):
        return repr(text)
    # text = text.replace('\\', '\\')
    text = text.replace("'", "''")
    return "'" + text + "'"
    
def escape(text):
    if not (isinstance(text, str)):
        return text
    #text = text.replace('\\', '\\\\')
    text = text.replace("'", "''")
    return "'" + text + "'"

class DatabaseModifer:

    def __init__(self, path):
        self.conn = sqlite3.connect(path)

    def add_column(self, name, type, default):
        sql = "create table from "

def execute(path, sql):
    db = sqlite3.connect(path)
    cursorobj = db.cursor()
    try:
        cursorobj.execute(sql)
        result = cursorobj.fetchall()
        db.commit()
    except Exception:
        raise
    db.close()
    return result

def execute(path, sql):
    db = sqlite3.connect(path)
    cursorobj = db.cursor()
    try:
        cursorobj.execute(sql)
        kv_result = []
        result = cursorobj.fetchall()
        for single in result:
            resultMap = {}
            for i, desc in enumerate(cursorobj.description):
                name = desc[0]
                resultMap[name] = single[i]
            kv_result.append(resultMap)
        db.commit()
        return kv_result
    except Exception:
        raise
    finally:
        db.close()
    
def get_update_sql(table, update_dict, condition_dict):
    """
    >>> from collections import OrderedDict;get_update_sql('test', OrderedDict(name='hello', age=10), dict(id=10))
    "update test set name='hello',age=10 where id=10"
    """
    update_str = "," .join(["%s=%s" % (name, to_sqlite_obj(update_dict[name])) for name in update_dict])
    condition_str = ",".join(["%s=%s" % (name, to_sqlite_obj(condition_dict[name])) for name in condition_dict])
    sql = "update %s set %s where %s" % (table, update_str, condition_str)
    return sql

def update(path, table, update_dict, condition_dict):
    sql = get_update_sql(table, update_dict, condition_dict)
    print(sql)
    return execute(path, sql)

def select(path, table, **kw):
    where_sql = ",".join(["%s=%s" % (name, to_sqlite_obj(kw[name])) for name in kw])
    sql = "select * from %s where %s" % (table, where_sql)
    return execute(path, sql)

class ObjDB:
    '''
    @staticmethod
    def getInstance():
        if not instance:
            instance = ObjDB()
        return instance'''
    
    def __init__(self, path):
        self.connect(path)
        
    def connect(self, path):
        dirname = util.utf8(os.path.dirname(__file__))
        self.path = os.path.join(dirname, path)
    
    def reconnect(self):
        # logger.info("connect %s" % self.path)
        self.db = sqlite3.connect(self.path)
        return self.db
    
    def done(self):
        self.db.close()
        
    def get_tables(self):
        return self.select("sqlite_master", "*")
        
    def get_table_desc(self, name):
        rs = self.execute("pragma table_info('%s')" % name)
        return rs
    
    def close(self):
        self.db.close()
        
    def select(self, table, names, where = None):
        db = self.reconnect()
        if names == '*':
            names_str = '*'
        else:
            names_str = ','.join(names)
        if where:
            where = "where %s" % where
        else:
            where = ""
        sql = "select %s from %s %s;" % (names_str, table, where) 
        logger.debug(sql)
        cursor = db.cursor()
        cursor.execute(sql)
        if names == '*':
            names = []
            for name_st in cursor.description:
                names.append(name_st[0])
        items = cursor.fetchall()
        result = []
        for item in items:
            d = {}
            for i, name in enumerate(names):
                d[name] = item[i]
            result.append(d)
        self.done()
        return result
    
    def execute(self, sql):
        db = self.reconnect()
        cursorobj = db.cursor()
        try:
            cursorobj.execute(sql)
            result = cursorobj.fetchall()
            db.commit()
        except Exception:
            raise
        db.close()
        return result
    
    def update(self, table, item):
        '''item is a dict, eg, {id:1, name:'text'}, id is required.'''
        db = self.reconnect()
        rows = []
        item = item.copy()
        id = item['id']
        del item['id']
        for key in item:
            if item[key] != None:
                row = '%s=%s' % (key, escape(item[key]))
            else:
                row = '%s=NULL' % key
            rows.append(row)
        sql = 'update %s set %s where id=%s' % (table, ','.join(rows), id)
        logger.warn(sql)
        db.execute(sql)
        db.commit()
        self.done()
    
    def get_new_id(self):
        data = None
        id = 0
        infos = self.select('pkm_info', '*')
        for info in infos:
            if info['key'] == 'max_id':
                id = int(info['value_start']) + 1
                data = info
                break
        if data:
            data['value_start'] = str(id)
            self.update('pkm_info', data)
        else:
            raise Exception("fatal error, info not found")
        return id
        
    def insert(self, table, d, newid = None):
        if 'id' in d:
            del d['id']
        keys = d.keys()
        values = [str(escape(x)) for x in d.values()]
        if newid == None:
            newid = self.get_new_id()
        sql = 'insert into %s (id, %s) values (%s, %s)' % (table, ','.join(keys), newid, ','.join(values))
        logger.warn(sql)
        db = self.reconnect()
        db.execute(sql)
        db.commit()
        self.done()
        return newid
        
    def search(self, table, d):
        cond = []
        for key in d:
            condition = "%s like %s" % (key, search_escape(d[key]))
            cond.append(condition)
        cond.append("state <> %s" % NO_SEARCH_STATE)
        return self.select(table, '*', ' and '.join(cond))
        # use select * from table where key1 like d[key1] and key2 like d[key2]
        

# 初始化KV存储
_leveldb = None
if leveldb:
    import xconfig
    _leveldb = leveldb.LevelDB(xconfig.DB_DIR)


class Table:

    def __init__(self, name):
        self.table_name = table_name

    def get_key(self, id):
        return self.table_name + ":" + id

    def get_by_id(self, id):
        key = self.get_key(id)
        return get(key)

    def update(self, id, obj):
        key = self.get_key(id)
        put(key, obj)

    def delete(self, id):
        key = self.get_key(id)
        delete(key)

    def count(self, func):
        pass

def timeseq():
    return "%020d" % int(time.time()*1000)

def get_object_from_bytes(bytes):
    obj = json.loads(bytes.decode("utf-8"))
    if isinstance(obj, dict):
        obj = Storage(**obj)
    return obj

def check_leveldb():
    if leveldb is None:
        raise Exception("leveldb not found!")

def get(key):
    check_leveldb()
    try:
        key = key.encode("utf-8")
        value = _leveldb.Get(key)
        return get_object_from_bytes(value)
    except KeyError:
        return None

def put(key, obj_value, sync = False):
    check_leveldb()
    
    key = key.encode("utf-8")
    # 注意json序列化有个问题，会把数字开头的key转成字符串
    value = json.dumps(obj_value)
    # print("Put %s = %s" % (key, value))
    _leveldb.Put(key, value.encode("utf-8"), sync = sync)

def delete(key, sync = False):
    check_leveldb()

    print("Delete %s" % key)
    key = key.encode("utf-8")
    _leveldb.Delete(key, sync = sync)

def scan(key_from = None, key_to = None, func = None, reverse = False):
    check_leveldb()

    if key_from:
        key_from = key_from.encode("utf-8")
    if key_to:
        key_to = key_to.encode("utf-8")
    iterator = _leveldb.RangeIter(key_from, key_to, include_value = True, reverse = reverse)
    for key, value in iterator:
        key = key.decode("utf-8")
        value = get_object_from_bytes(value)
        if not func(key, value):
            break

def prefix_scan(prefix, func, reverse = False):
    check_leveldb()

    key_from = None
    key_to = None

    origin_prefix = prefix
    prefix = prefix.encode("utf-8")

    if reverse:
        key_to = prefix
    else:
        key_from = prefix

    iterator = _leveldb.RangeIter(key_from, key_to, include_value = True, reverse = reverse)

    offset = 0
    for key, value in iterator:
        key = key.decode("utf-8")
        if not key.startswith(origin_prefix):
            break
        value = get_object_from_bytes(value)
        if not func(key, value):
            break
        offset += 1

def prefix_list(prefix, filter_func = None, offset = 0, limit = -1, reverse = False, include_key = False):
    return list(prefix_iter(prefix, filter_func, offset, limit, reverse, include_key))

def prefix_iter(prefix, filter_func = None, offset = 0, limit = -1, reverse = False, include_key = False):
    """通过前缀查询
    @param {string} prefix 遍历前缀
    @param {function} filter_func 过滤函数
    @param {int} offset 选择的开始下标，包含
    @param {int} limit  选择的数据行数
    @param {boolean} reverse 是否反向遍历
    @param {boolean} include_key 返回的数据是否包含key，默认只有value
    """
    check_leveldb()

    origin_prefix = prefix

    if reverse:
        # 时序表的主键为 表名:用户名:时间序列 时间序列长度为20
        prefix += ":9"

    prefix   = prefix.encode("utf-8")
    # print("prefix: %s, origin_prefix: %s, reverse: %s" % (prefix, origin_prefix, reverse))
    if reverse:
        iterator = _leveldb.RangeIter(None, prefix, include_value = True, reverse = reverse)
    else:
        iterator = _leveldb.RangeIter(prefix, None, include_value = True, reverse = reverse)

    position       = 0
    matched_offset = 0
    result_size    = 0

    for key, value in iterator:
        key = key.decode("utf-8")
        if not key.startswith(origin_prefix):
            break
        value = get_object_from_bytes(value)
        if filter_func is None or filter_func(key, value):
            if matched_offset >= offset:
                result_size += 1
                if include_key:
                    yield key, value
                else:
                    yield value
            matched_offset += 1

        if limit > 0 and result_size >= limit:
            break
        position += 1


def count(key_from = None, key_to = None, filter_func = None):
    check_leveldb()

    if key_from:
        key_from = key_from.encode("utf-8")
    if key_to:
        key_to = key_to.encode("utf-8")
    iterator = _leveldb.RangeIter(key_from, key_to, include_value = True)
    count = 0
    for key, value in iterator:
        key = key.decode("utf-8")
        value = get_object_from_bytes(value)
        if filter_func(key, value):
            count += 1
    return count

def prefix_count(prefix, filter_func = None):
    count = [0]
    def func(key, value):
        if not key.startswith(prefix):
            return False
        if filter_func is None:
            count[0] += 1
        elif filter_func(key, value):
            count[0] += 1
        return True
    prefix_scan(prefix, func)
    return count[0]

def zadd(key, score, member):
    obj = get(key)
    # print("zadd %r %r" % (member, score))
    if obj != None:
        obj[member] = score
        put(key, obj)
    else:
        obj = dict()
        obj[member] = score
        put(key, obj)

def zrange(key, start, stop):
    """zset分片，不同于Python，这里是左右包含，包含start，包含stop，默认从小到大排序
    :arg int start: 从0开始，负数表示倒数
    :arg int stop: 从0开始，负数表示倒数
    TODO 优化排序算法，使用有序列表+哈希表
    """
    obj = get(key)
    if obj != None:
        items = obj.items()
        length = len(items)

        if stop < 0:
            stop += length + 1
        if start < 0:
            start += length + 1

        sorted_items = sorted(items, key = lambda x: x[1])
        sorted_keys = [k[0] for k in sorted_items]
        if stop < start:
            # 需要逆序
            stop -= 1
            start += 1
            found = sorted_keys[stop: start]
            found.reverse()
            return found
        return sorted_keys[start: stop]
    return []

def zcount(key):
    obj = get(key)
    if obj != None:
        return len(obj)
    return 0

def zscore(key, member):
    obj = get(key)
    if obj != None:
        return obj.get(member)
    return None

def zrem(key, member):
    obj = get(key)
    if obj != None:
        del obj[member]
        put(key, obj)
    return None

if __name__ == "__main__":
    db = ObjDB('pkm.db')
    d = {"id":7}
    r = db.select("pkm_data", "*", "id=7")
    for i in r:
        print(i)
    
    