from flask import render_template, current_app, jsonify, request, g

from . import index_blu
from info.models import User, News, Category, Comment, CommentLike
from info.utils.response_code import RET
from info import constants, db
from info.utils.commons import login_required


@index_blu.route('/')
@login_required
def index():
    user = g.user
    # 获取点击排行数据
    news_list = None
    try:
        # 默认实现是按照新闻点击次数进行查询，并且分页6条数据
        news_list = News.query.order_by(News.clicks.desc()).limit(6)
    except Exception as e:
        current_app.logger.error(e)
    # 判断查询结果是否有数据
    if not news_list:
        return jsonify(errno=RET.NODATA, errmsg='无新闻排行数据')
    # 如果有数据,定义容器来存储新闻数据
    click_news_list = []
    # 遍历查询结果的对象
    for news in news_list if news_list else None:
        # 模型类中定义的方法，获取对象的数据，类似于__repr__方法的作用
        click_news_list.append(news.to_dict())

    # 获取新闻分类数据
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询分类数据失败')
    # 判断查询结果
    if not categories:
        return jsonify(errno=RET.NODATA, errmsg='无分类数据')
    # 定义容器，用来存储遍历的查询对象
    categories_list = []

    for category in categories:
        categories_list.append(category.to_dict())

    data = {
        'user_info': user.to_dict() if user else None,
        'click_news_list': click_news_list,
        'categories_list': categories_list
    }
    return render_template('news/index.html', data=data)


@index_blu.route('/news_list')
@login_required
def get_news_list():
    """
    获取指定分类的新闻列表
    """
    # 获取参数
    cid = request.args.get('cid', '1')
    page = request.args.get('page', '1')
    per_page = request.args.get('per_page', '10')

    # 校验参数
    try:
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    # 查询数据并分页
    filters = [News.status == 0]
    # 如果分类id大于1，那么添加分类id的过滤
    if cid > 1:
        filters.append(News.category_id == cid)
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, constants.HOME_PAGE_MAX_NEWS, False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据失败')
    # 获取查询出来的数据
    items = paginate.items
    # 获取到的总页数
    total_page = paginate.pages
    current_page = paginate.page
    news_dict_list = []
    for news in items:
        news_dict_list.append(news.to_dict())


    # 返回数据
    data = {
        'news_dict_list': news_dict_list,
        'total_page': total_page,
        'current_page': current_page
    }
    return jsonify(errno=RET.OK, errmsg='OK', data=data)


@index_blu.route('/<int:news_id>')
@login_required
def get_news_detail(news_id):
    """
    新闻详情页面
    """
    user = g.user
    # 根据新闻id查询数据库
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据错误')
    # 检查查询结果
    if not news:
        return jsonify(errno=RET.NODATA, errmsg='无新闻数据')

    # 新闻详情的点击次数+1
    news.clicks += 1
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存数据失败')
    # 收藏,默认为False，如果用户已登录，并且该新闻已被登录用户收藏
    is_collected = False
    if user and news in user.collection_news:
        is_collected = True

    # 新闻评论列表
    comments = []
    try:
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
    comment_like_ids = []
    # 获取当前登录用户的所有评论的id，
    if user:
        try:
            comment_ids = [comment.id for comment in comments]
            # 再查询点赞了哪些评论
            comment_likes = CommentLike.query.filter(CommentLike.comment_id.in_(comment_ids),
                                                     CommentLike.user_id == user.id).all()
            # 遍历点赞的评论数据,获取
            comment_like_ids = [comment_like.comment_id for comment_like in comment_likes]
        except Exception as e:
            current_app.logger.error(e)
    comment_dict_li = []
    for comment in comments:
        comment_dict = comment.to_dict()
        # 如果未点赞
        comment_dict['is_like'] = False
        # 如果点赞
        if comment.id in comment_like_ids:
            comment_dict['is_like'] = True
        comment_dict_li.append(comment_dict)

    is_followed = False
    # 用户关注新闻的发布者，即登录用户关注作者
    if news.user and user:
        if news.user in user.followers:
            is_followed = True

    # 获取点击排行数据
    news_list = None
    try:
        # 默认实现是按照新闻点击次数进行查询，并且分页6条数据
        news_list = News.query.order_by(News.clicks.desc()).limit(6)
    except Exception as e:
        current_app.logger.error(e)
    # 判断查询结果是否有数据
    if not news_list:
        return jsonify(errno=RET.NODATA, errmsg='无新闻排行数据')
    # 如果有数据,定义容器来存储新闻数据
    click_news_list = []
    # 遍历查询结果的对象
    for index in news_list if news_list else None:
        # 模型类中定义的方法，获取对象的数据，类似于__repr__方法的作用
        click_news_list.append(index.to_dict())

    data = {
        'news': news.to_dict(),
        'user_info': user.to_dict() if user else None,
        'click_news_list': click_news_list,
        'is_collected': is_collected,
        'is_followed': is_followed,
        'comments': comment_dict_li
    }

    # 调用模板页面返回数据
    return render_template('news/detail.html', data=data)


@index_blu.route('/news_collect', methods=['POST'])
@login_required
def news_collect():
    """
    收藏或取消收藏
    """
    # 获取用户信息
    user = g.user
    # 判断用户是否登录
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')
    # 获取参数
    news_id = request.json.get('news_id')
    action = request.json.get('action')
    # 校验参数
    try:
        news_id = int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数格式错误')
    if action not in ['collect', 'cancel_collect']:
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    # 根据news_id查询数据库
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据错误')
    if not news:
        return jsonify(errno=RET.NODATA, errmsg='无新闻数据')
    # 判断用户收藏还是取消收藏
    if action == 'collect':
        # 判断是否收藏过
        if news not in user.collection_news:
            user.collection_news.append(news)
    else:
        user.collection_news.remove(news)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存数据失败')
    return jsonify(errno=RET.OK, errmsg='操作成功')


@index_blu.route('/followed_user',methods=['POST'])
@login_required
def followed_user():
    """
    关注与取消关注
    """
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')
    user_id = request.json.get('user_id')
    action = request.json.get('action')

    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')
    if action not in ['follow', 'unfollow']:
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据错误')
    if not other:
        return jsonify(errno=RET.NODATA, errmsg='无用户数据')
    if action == 'follow':
        if other not in user.followed:
            user.followed.append(other)
        else:
            return jsonify(errno=RET.DATAEXIST, errmsg='当前用户已被关注')
    else:
        if other in user.followed:
            user.followed.remove(other)
        else:
            return jsonify(errno=RET.DATAEXIST, errmsg='当前用户未被关注')
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
    return jsonify(errno=RET.OK, errmsg='OK')


@index_blu.route('/news_comment', methods=['POST'])
@login_required
def comment_news():
    """
    评论新闻
    """
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')

    news_id = request.json.get('news_id')
    comment_conent = request.json.get('comment')
    parent_id = request.json.get('parent_id')
    if not all([news_id, comment_conent]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    try:
        news_id = int(news_id)
        if parent_id:
            parent_id = int(parent_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询错误')
    if not news:
        return jsonify(errno=RET.NODATA, errmsg='无新闻数据')
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news.id
    comment.content = comment_conent
    if parent_id:
        comment.parent_id = parent_id
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()

    return jsonify(errno=RET.OK, errmsg='OK', data=comment.to_dict())


@index_blu.route('/comment_like', methods=['POST'])
@login_required
def comment_like():
    """
    点赞和取消点赞
    """
    user = g.user
    comment_id = request.json.get('comment_id')
    action = request.json.get('action')
    if not all([comment_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    if action not in ('add', 'remove'):
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    try:
        comment_id = int(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据错误')
    if not comment:
        return jsonify(errno=RET.NODATA, errmsg='评论不存在')
    if action == 'add':
        comment_like_model = CommentLike.query.filter(CommentLike.user_id == user.id,CommentLike.comment_id == comment_id).first()

        if not comment_like_model:
            comment_like_model = CommentLike()
            comment_like_model.user_id = user.id
            comment_like_model.comment_id = comment.id
            db.session.add(comment_like_model)
            comment.like_count += 1
    else:
        comment_like_model = CommentLike.query.filter(CommentLike.user_id == user.id,CommentLike.comment_id == comment_id).first()
        if comment_like_model:
            db.session.delete(comment_like_model)
            comment.like_count -= 1
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存数据失败')
    return jsonify(errno=RET.OK, errmsg='OK')


# 网站图标展示
@index_blu.route('/favicon.ico')
def favicon_ico():
    # 使用应用上下文调用Flask内置的发送静态文件的方法，发送一个文件，给浏览器
    return current_app.send_static_file('news/favicon.ico')