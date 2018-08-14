from qiniu import Auth, put_data

access_key = 'DvKJ33hDK3EN-1bt9tz3zW0B0tVQyibTCKofHSC6'
secret_key = 'N44RU2gs--u_zOUgql_6YJ5DG6wUMyoiVJtvGbhu'

bucket_name = 'info'


def storage(data):
    try:
        q = Auth(access_key, secret_key)
        token = q.upload_token(bucket_name)
        ret, info = put_data(token, None, data)
        print(ret, info)
    except Exception as e:
        raise e;

    if info.status_code != 200:
        raise Exception("上传图片失败")
    return ret["key"]


if __name__ == '__main__':
    file = input('请输入文件路径')
    with open(file, 'rb') as f:
        storage(f.read())