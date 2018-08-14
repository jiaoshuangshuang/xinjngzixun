from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
# 导入info模块创建的程序实例app
from info import create_app, db
from info import models
from info.models import User

# 调用工厂方法，获取app
app = create_app('development')

# 实力化管理器对象
manager = Manager(app)

# 使用迁移框架
Migrate(app, db)
# 通过管理器对象，添加迁移命令
manager.add_command('db', MigrateCommand)

# 创建管理员用户
@manager.option('-n','-name',dest='name')
@manager.option('-p','-password',dest='password')
def create_supperuser(name,password):
    if not all([name,password]):
        print('参数缺失')
    user = User()
    user.nick_name = name
    user.mobile = name
    user.password = password
    user.is_admin = True
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(e)
    print('管理员创建成功')

if __name__ == '__main__':
    manager.run()
