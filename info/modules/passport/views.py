import re, random
from datetime import datetime
from flask import request, current_app, jsonify, make_response, session

from . import passport_blu
from info.utils.response_code import RET
from info.utils.captcha.captcha import captcha
from info import constants, redis_store
from info.models import User
from info.libs.yuntongxun import sms
from info import db


@passport_blu.route('/image_code')
def generate_image_code():
    """
    生成图片验证码
    """
    # 获取参数
    image_code_id = request.args.get('image_code_id')
    # 校验参数
    if not image_code_id:
        return jsonify(errno=RET.PARAMERR, errmsg='获取参数失败')
    # 生成验证码
    name, text, image = captcha.generate_captcha()
    # 保存图片验证码到redis数据库
    try:
        redis_store.setex('ImageCode_'+image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        # 使用应用上下文记录操作redis数据库的错误信息
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmag='保存图片验证码失败')
    # 如果没有发生异常，直接返回图片
    else:
        # 使用响应对象返回图片本身
        resp = make_response(image)
        # 修改响应头，改成图片格式
        resp.headers['Content-Type'] = 'image/jpg'
        return resp


@passport_blu.route('/sms_code', methods=['POST'])
def send_sms_code():
    """
    发送短信验证码
    """
    # 获取参数
    mobile = request.json.get('mobile')
    image_code = request.json.get('image_code')
    image_code_id = request.json.get("image_code_id")
    # 判断参数是否完整
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')
    # 判断手机号的格式是否正确
    if not re.match(r'1[3456789]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式不正确')
    # 获取本地redis数据库中存储的真实的图片验证码
    try:
        real_image_code = redis_store.get('ImageCode_'+image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据查询错误')
    # 检查获取结果
    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg='图片验证码已过期')
    # 删除图片验证码
    try:
        redis_store.delete('ImageCode_'+image_code_id)
    except Exception as e:
        current_app.logger.error(e)
    # 比较redis数据库中存储的真实图片验证码和用户输入的是否一致,忽略大小写
    if image_code.lower() != real_image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg='图片验证码不一致')
    # 查询数据库，检查手机号是否已注册过
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户数据失败')
    if user is not None:
        return jsonify(errno=RET.DATAEXIST, errmsg='手机号已注册过')
    # 生成短信随机数
    sms_code = '%06d' % random.randint(0, 999999)
    # 把短信随机数存入本地redis数据库中
    try:
        redis_store.setex('SMSCode_'+mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存短信数据失败')
    # 调用第三方软件云通讯发送短信
    try:
        ccp = sms.CCP()
        result = ccp.send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], 1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='发送短信失败')
    else:

        # 判断发送结果
        if result == 0:
            return jsonify(errno=RET.OK, errmsg='发送成功')
        else:
            return jsonify(errno=RET.THIRDERR, errmsg='发送失败')


@passport_blu.route('/register', methods=['POST'])
def register():
    """
    注册
    """
    # 获取参数
    mobile = request.json.get('mobile')
    sms_code = request.json.get('sms_code')
    password = request.json.get('password')
    # 判断参数是否完整
    if not all ([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')
    # 判断手机号的格式
    if not re.match(r'1[3456789]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='请输入正确的手机号')

    # 从redis中获取指定手机号对应的短信验证码
    try:
        real_sms_code = redis_store.get('SMSCode_'+mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据失败')
    if not real_sms_code:
        return jsonify(errno=RET.NODATA, errmsg='短信验证码已过期')
    # 校验验证码
    if sms_code != real_sms_code:
        return jsonify(errno=RET.DATAERR, errmsg='短信验证码错误')
    # 删除redis数据库中存储的短信验证码
    try:
        redis_store.delete('SMSCode_'+mobile)
    except Exception as e:
        current_app.logger.error(e)

    # 检查手机号是否注册过
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据失败')
    if user:
        return jsonify(errno=RET.DATAERR, errmsg='手机号已注册过')
    # 初始化 user 模型，并设置数据并添加到数据库
    user = User()
    user.mobile = mobile
    user.nick_name = mobile
    user.password = password
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 提交数据如果发生异常，需要进行回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='数据保存错误')
    # 保存当前用户的登陆状态
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['user_mobile'] = user.mobile

    return jsonify(errno=RET.OK, errmsg='注册成功')


@passport_blu.route('/login', methods=['POST'])
def login():
    """
    登陆
    """
    # 获取参数
    mobile = request.json.get('mobile')
    password = request.json.get('password')
    # 检查参数的完整性
    if not all ([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')
    # 判断手机号的格式
    if not re.match(r'1[3456789]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='请输入正确的手机号')
    # 从数据库查询出指定的用户
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据失败')
    # 校验密码
    if not user or not user.check_password(password):
        return jsonify(errno=RET.DATAERR, errmsg='用户名或密码错误')
    # 保存用户登录状态
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile
    # 登录时间
    user.last_login = datetime.now()

    return jsonify(errno=RET.OK, errmsg='登陆成功')


@passport_blu.route('/logout', methods=['POST'])
def logout():
    """
    退出登陆
    清除session中的对应登录之后保存的信息
    """
    session.pop('user_id', None)
    session.pop('nick_name', None)
    session.pop('mobile', None)
    session.pop('is_admin', None)

    return jsonify(errno=RET.OK, errmsg='退出成功')