from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
# 导入info模块创建的程序实例app
from info import create_app, db
from info import models

# 调用工厂方法，获取app
app = create_app('development')

# 实力化管理器对象
manager = Manager(app)

# 使用迁移框架
Migrate(app, db)
# 通过管理器对象，添加迁移命令
manager.add_command('db', MigrateCommand)

@app.route('/index')
def index():
    return 'index'

if __name__ == '__main__':
    manager.run()
