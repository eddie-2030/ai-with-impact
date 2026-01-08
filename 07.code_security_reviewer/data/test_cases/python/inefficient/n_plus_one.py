# INEFFICIENT: N+1 Query Problem
# This code makes multiple database queries in a loop

from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

def get_user_posts(user_ids):
    """INEFFICIENT: N+1 query problem - makes N+1 database queries"""
    users = User.objects.filter(id__in=user_ids)
    result = []
    
    # INEFFICIENT: Makes one query per user (N queries)
    for user in users:
        posts = Post.objects.filter(user_id=user.id)  # N queries!
        result.append({
            'user': user,
            'posts': list(posts)
        })
    
    return result

def get_all_posts():
    """INEFFICIENT: Multiple queries for related data"""
    posts = Post.objects.all()
    result = []
    
    # INEFFICIENT: One query per post to get user
    for post in posts:
        user = User.objects.get(id=post.user_id)  # N queries!
        result.append({
            'post': post,
            'user': user
        })
    
    return result

