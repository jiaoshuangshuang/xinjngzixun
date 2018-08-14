from flask import Flask, g, render_template
from flask_sqlalchemy import SQLAlchemy
# 导入配置对象
from config import config, Config
# 指定session信息的存储
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from flask_wtf import csrf
# 导入日志模块
import logging
# 日志的文件处理模块
from logging.handlers import RotatingFileHandler
from redis import StrictRedis

# SQLAlchemy数据库实例
db = SQLAlchemy()

# 实例化redis数据库，保存的是缓存数据，比如图片验证码、短信验证码
redis_store = StrictRedis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)

# 设置日志的记录等级
logging.basicConfig(level=logging.DEBUG) # 调试debug级
# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024*1024*100, backupCount=10)
# 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
# 为刚创建的日志记录器设置日志记录格式
file_log_handler.setFormatter(formatter)
# 为全局的日志工具对象（flask app使用的）添加日志记录器
logging.getLogger().addHandler(file_log_handler)

# 定义工厂方法，创建程序实例,动态的传入配置信息
def create_app(config_name):
    app = Flask(__name__)
    # 使用配置对象
    app.config.from_object(config[config_name])

    # 把sqlalchemy对象和app进行关联
    db.init_app(app)

    # 把Session对象和app关联
    Session(app)
    # csrf实例化,实现跨站请求保护
    CSRFProtect(app)

    # 通过请求钩子，把服务器生成token写入到客户端浏览器中
    @app.after_request
    def after_request(response):
        csrf_token = csrf.generate_csrf()
        response.set_cookie('csrf_token', csrf_token)
        return response

    # 注册蓝图
    from info.modules.index import index_blu
    # 新闻模块
    app.register_blueprint(index_blu)
    # 注册登录模块
    from info.modules.passport import passport_blu
    app.register_blueprint(passport_blu)
    # 个人中心模块蓝
    from info.modules.profile import profile_blu
    app.register_blueprint(profile_blu)
    # 管理员中心模块
    from info.modules.admin import admin_blu
    app.register_blueprint(admin_blu)

    # 添加自定义过滤器
    from info.utils.commons import do_index_class
    app.add_template_filter(do_index_class, 'index_class')

    # 在用户访问一些不存在网址的时候弹出404页面
    from info.utils.commons import login_required
    @app.errorhandler(404)
    @login_required
    def page_not_found(_):
        user = g.user
        data = {"user_info": user.to_dict() if user else None}
        return render_template('news/404.html', data=data)


    return app