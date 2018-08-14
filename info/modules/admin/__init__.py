from flask import Blueprint, session, request, url_for, redirect

admin_blu = Blueprint('admin', __name__, url_prefix='/admin')

from . import views

@admin_blu.before_request
def check_admin():
    # if 不是管理员，那么直接跳转到主页
    is_admin = session.get("is_admin", False)
    # if not is_admin and 当前访问的url不是管理登录页:
    if not is_admin and not request.url.endswith(url_for('admin.login')):
        return redirect('/')