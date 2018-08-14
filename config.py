from redis import StrictRedis

class Config(object):
    # 调试模式
    DEBUG = True

    # 设置密钥
    SECRET_KEY = 'KysxRWnnqWRn/c0K7WmXoFjjShEiRoCWHmyCkRZUz3U='
    # 配置数据库的连接
    SQLALCHEMY_DATABASE_URI = 'mysql://root:mysql@localhost/info'
    # 动态追踪修改
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 配置redis的主机和端口
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379

    SESSION_TYPE = 'redis'
    # 实例化redis对象
    SESSION_REDIS = StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    # 对session信息进行签名
    SESSION_USE_SIGNER = True
    # 指定session信息过期时间
    PERMANENT_SESSION_LIFETIME = 86400


# 开发者模式
class developmentConfig(Config):
    DEBUG = True


# 生产模式
class productionConfig(Config):
    DEBUG = False


# 通过字典映射配置对象
config = {
    'development': developmentConfig,
    'production': productionConfig
}
