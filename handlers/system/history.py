# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/03/03 12:46:20
# @modified 2018/12/21 21:56:19
import xtemplate
import xauth
import xutils
import xconfig
from xutils import History

class HistoryHandler(object):
    """docstring for HistoryHandler"""

    @xauth.login_required("admin")
    def GET(self):
        xutils.get_argument("type", "")
        items = []
        if xconfig.search_history:
            items = xconfig.search_history.recent(50);
        return xtemplate.render("system/history.html", 
            show_aside = False,
            items = items)
        

xurls = (
    r"/system/history", HistoryHandler
)