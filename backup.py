import zipfile
import os
from util import dateutil
from util import fsutil
from util import logutil
import config
import re
import time

class T:
    pass

_black_list = [".zip", ".pyc", ".pdf", "__pycache__"]

_dirname = os.path.dirname(__file__)

_zipname = "xnote.zip"

_dest_path = os.path.join(_dirname, "static", _zipname)

def zip_xnote(nameblacklist = [_zipname]):
    dirname = os.path.dirname(__file__)
    fp = open(_dest_path, "w")
    fp.close()
    zf = zipfile.ZipFile(_dest_path, "w")
    for root, dirs, files in os.walk(dirname):
        for fname in files:
            if fname in nameblacklist:
                continue
            name, ext = os.path.splitext(fname)
            if ext in _black_list or ext in nameblacklist:
                continue
            path = os.path.join(root, fname)
            try:
                st = os.stat(path)
                if st.st_size > config.MAX_FILE_SIZE:
                    continue
            except:
                continue
            arcname = path[len(dirname):]
            zf.write(path, arcname)
    zf.close()

def zip_new_xnote():
    zip_xnote([_zipname, ".db", ".log", ".exe"])

def get_info():
    info = T()
    info.path = _dest_path

    if os.path.exists(_dest_path):
        info.name = _zipname
        info.path = _dest_path
        st = os.stat(_dest_path)
        info.mtime = dateutil.format_time(st.st_mtime)
        info.size = fsutil.format_size(st.st_size)
    else:
        info.name = None
        info.path = None
        info.mtime = None
        info.size = None
    return info


def backup_db():
    now = time.strftime("%Y%m%d")
    dbname = "data.{}.db".format(now)
    dbpath = config.get("DB_PATH")
    backup_dir = config.get("BACKUP_DIR")
    newdbpath = os.path.join(backup_dir, dbname)
    fsutil.copy(dbpath, newdbpath)

def chk_backup():
    backup_dir = config.get("BACKUP_DIR")
    files = os.listdir(backup_dir)
    sorted_files = sorted(files)
    logutil.info("sorted backup files: {}", sorted_files)
    if len(sorted_files) > 3:
        target = sorted_files[0]
        fsutil.remove(os.path.join(backup_dir, target))
        logutil.warn("remove file {}", target)
    if len(sorted_files) == 0:
        backup_db()
    else:
        lastfile = sorted_files[-1]
        p = re.compile(r"data\.(\d+)\.db")
        m = p.match(lastfile)
        if m:
            data = m.groups()[0]
            tm_time = time.strptime(data, "%Y%m%d")
            seconds = time.mktime(tm_time)
            now = time.time()
            # backup every 10 days.
            if now - seconds > 3600 * 24 * 10:
                backup_db()
        else:
            fsutil.remove(os.path.join(backup_dir, lastfile))
            logutil.warn("not valid db backup file, remove {}", lastfile)
    