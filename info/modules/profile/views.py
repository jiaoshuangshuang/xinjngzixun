from flask import g, redirect, render_template, request, jsonify, current_app, session, abort

from . import profile_blu
# 导入登录验证装饰器
from info.utils.commons import login_required
# 导入自定义的状态码
from info.utils.response_code import RET
# 导入SQLAlchemy对象
from info import db,constants
# 导入七牛云
from info.utils.image_storage import storage
# 导入模型类
from info.models import Category, News, User


@profile_blu.route('/info')
@login_required
def user_info():
    """
    用户信息页面
    """
    user = g.user
    # 判断用户是否登录
    if not user:
        return redirect('/')
    # 调用模型类中的方法，获取用户的基本信息
    data = {
        'user':user.to_dict()
    }
    # 默认加载模板页面
    return render_template('news/user.html',data=data)


@profile_blu.route('/base_info',methods=['POST','GET'])
@login_required
def base_info():
    """
    个人信息修改
    """
    user = g.user
    if request.method == 'GET':
        data = {
            'user':user.to_dict()
        }
        return render_template('news/user_base_info.html',data=data)
    # 如果是post请求，获取参数
    nick_name = request.json.get('nick_name')
    signature = request.json.get('signature')
    gender = request.json.get('gender')
    # 判断参数的完整性
    if not all([nick_name,signature,gender]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 判断用户选择的性别
    if gender not in ['MAN','WOMEN']:
        return jsonify(errno=RET.PARAMERR,errmsg='参数格式错误')
    # 保存用户数据
    user.nick_name = nick_name
    user.signature = signature
    user.gender = gender
    # 提交数据到数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存用户信息失败')
    # 需要及时的更新缓存中的信息
    session['nick_name'] = user.nick_name
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK')


@profile_blu.route('/pic_info',methods=['GET','POST'])
@login_required
def pic_info():
    """
    个人中心：上传头像
    """
    user = g.user
    if request.method == 'GET':
        data = {
            'user':user.to_dict()
        }
        return render_template('news/user_pic_info.html',data=data)
    # 获取前端post请求的图片文件
    avatar = request.files.get('avatar')
    # 校验参数的存在
    if not avatar:
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    # 读取图片数据
    try:
        avatar_data = avatar.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg='参数格式错误')
    # 调用七牛云，实现图片的上传,保存图片名称
    try:
        image_name = storage(avatar_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg='上传图片失败')
    # 保存图片数据到用户数据中,保存的是图片的相对路径（名称）
    user.avatar_url = image_name
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 拼接图片的绝对路径，七牛云的空间外链域名+图片名称
    avatar_url = constants.QINIU_DOMIN_PREFIX + image_name
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK',data={'avatar_url':avatar_url})


@profile_blu.route("/pass_info",methods=['GET','POST'])
@login_required
def pass_info():
    """
    个人中心：修改密码
    """
    # 如果是get请求,默认渲染模板页面
    if request.method == 'GET':
        return render_template('news/user_pass_info.html')
    # 获取参数
    old_password = request.json.get('old_password')
    new_password = request.json.get('new_password')
    # 检查参数的完整性
    if not all([old_password,new_password]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 获取用户的登录信息
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg='用户未登录')
    # 校验密码是否正确
    if not user.check_password(old_password):
        return jsonify(errno=RET.PWDERR,errmsg='旧密码错误')
    # 如果旧密码正确，更新新密码到数据库
    user.password = new_password
    # 提交数据到数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK')


@profile_blu.route('/news_release',methods=['GET','POST'])
@login_required
def news_release():
    """
    个人中心：新闻发布
    """
    # 获取用户信息
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')
    if request.method == 'GET':
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg='查询数据失败')
        # 检查查询结果是否有数据
        if not categories:
            return jsonify(errno=RET.NODATA,errmsg='无分类数据')
        # 定义容器，存储新闻分类的字典数据
        category_list = []
        for category in categories:
            category_list.append(category.to_dict())
        # 移除新闻分类的id为1(最新)
        category_list.pop(0)
        data = {
            'categories':category_list
        }
        return render_template('news/user_news_release.html',data=data)
    # 获取post请求的参数
    title = request.form.get('title')
    category_id = request.form.get('category_id')
    digest = request.form.get('digest')
    index_image = request.files.get('index_image')
    content = request.form.get('content')
    print(title,category_id,digest,index_image,content)
    # 检查参数的完整性
    if not all([title,category_id,digest,index_image,content]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 把分类id转成int
    try:
        category_id = int(category_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg='参数类型错误')
    # 读取图片数据，调用七牛云上传新闻图片
    try:
        index_image_data = index_image.read()
        image_name = storage(index_image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg='上传图片失败')

    # 构造模型类对象,保存新闻数据
    news = News()
    news.title = title
    news.category_id = category_id
    news.digest = digest
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + image_name
    news.source = '个人发布'
    news.content = content
    news.user_id = user.id
    news.status = 1
    # 提交数据到数据库中
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK')


@profile_blu.route('/news_list')
@login_required
def user_news_list():
    """
    用户新闻列表
    """
    page = request.args.get('p','1')
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    user = g.user
    news_list = []
    total_page = 1
    current_page = 1
    try:
        paginate = News.query.filter(News.user_id==user.id).paginate(page,constants.USER_COLLECTION_MAX_NEWS,False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据错误')
    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_review_dict())
    data = {
        'news_list':news_dict_list,
        'total_page':total_page,
        'current_page':current_page
    }
    return render_template('news/user_news_list.html',data=data)



@profile_blu.route('/user_follow')
@login_required
def user_follow():
    """
    用户关注
    """
    page = request.args.get('p','1')
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
    user = g.user
    follows = []
    current_page = 1
    total_page = 1
    try:
        paginate = user.followed.paginate(page,constants.USER_FOLLOWED_MAX_COUNT,False)
        current_page = paginate.page
        total_page = paginate.pages
        follows = paginate.items
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据错误')
    user_follow_list = []
    for follow in follows:
        user_follow_list.append(follow.to_dict())
    data = {
        'users':user_follow_list,
        'current_page':current_page,
        'total_page':total_page
    }
    return render_template('news/user_follow.html',data=data)


@profile_blu.route('/other_info')
@login_required
def other_info():
    """
    查询用户关注的其他用户信息
    """
    user = g.user
    other_id = request.args.get('user_id')
    if not other_id:
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    try:
        other = User.query.get(other_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据错误')
    if not other:
        return jsonify(errno=RET.NODATA,errmsg='无数据')

    is_follwed = False
    if other and user:
        if other in user.followed:
            is_follwed = True
    data = {
        'is_followed':is_follwed,
        'user':user.to_dict() if user else None,
        'other_info':other.to_dict()
    }
    return render_template('news/other.html',data=data)


@profile_blu.route('/other_news_list')
def other_news_list():
    """
    返回指定用户发布的新闻
    """
    user_id = request.args.get('user_id')
    page = request.args.get('p', '1')

    if not all([page, user_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')

    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据库错误')
    if not other:
        return jsonify(errno=RET.NODATA,errmsg='用户不存在')
    try:
        paginate = News.query.filter(News.user_id == other.id).paginate(page,constants.USER_COLLECTION_MAX_NEWS,False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据错误')
    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_basic_dict())
    data = {
        'news_list':news_dict_list,
        'total_page':total_page,
        'current_page':current_page
    }
    return jsonify(errno=RET.OK,errmsg='OK',data=data)


@profile_blu.route('/collection')
@login_required
def user_collection():
    """
    用户收藏
    """

    page = request.args.get('p','1')
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    user = g.user
    news_list = []
    total_page = 1
    current_page = 1
    try:
        paginate = user.collection_news.paginate(page,constants.USER_COLLECTION_MAX_NEWS,False)
        current_page = paginate.page
        total_page = paginate.pages
        news_list = paginate.items
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_basic_dict())

    data = {
        'collections':news_dict_list,
        'total_page':total_page,
        'current_page':current_page,
    }

    return render_template('news/user_collection.html',data=data)