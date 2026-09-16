import os
import pwd

from django.db import connection
from django.http import JsonResponse


def whoami(request):
    """3層のうち「コンテナ内のLinuxユーザー」と「DBユーザー」を返す。"""
    uid = os.getuid()
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        db_user = cursor.fetchone()[0]
    return JsonResponse(
        {
            "linux_user": pwd.getpwuid(uid).pw_name,
            "uid": uid,
            "gid": os.getgid(),
            "db_user": db_user,
        }
    )
