from info.models import User
from flask import session, current_app, g
import functools

# 自定义过滤器，过滤点击排序html的class
def do_index_class(index):
    if index == 0:
        return 'first'
    elif index == 1:
        return 'second'
    elif index == 2:
        return 'third'
    else:
        return ''

# 检查用户是否登录，装饰器实现
def login_required(f):
    # 让被装饰的函数的属性不会被改变
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # 尝试获取用户的登录信息
        user_id = session.get('user_id')
        user = None
        if user_id:
            try:
                user = User.query.get(user_id)
            except Exception as e:
                current_app.logger.error(e)
        # 使用g对象来保存用户信息
        g.user = user
        return f(*args, **kwargs)
        # 让被装饰的函数的名称在返回wapper之前赋值给wrapper的__name__
        # wrapper.__name__ = f.__name__
    return wrapper