# EFFICIENT: Eager Loading
# This code uses eager loading to reduce database queries

from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

def get_user_posts(user_ids):
    """EFFICIENT: Uses eager loading - only 2 queries total"""
    # EFFICIENT: Prefetch related data in one query
    users = User.objects.filter(id__in=user_ids).prefetch_related('post_set')
    result = []
    
    # EFFICIENT: No additional queries needed
    for user in users:
        result.append({
            'user': user,
            'posts': list(user.post_set.all())
        })
    
    return result

def get_all_posts():
    """EFFICIENT: Uses select_related to join in one query"""
    # EFFICIENT: Joins user data in single query
    posts = Post.objects.select_related('user').all()
    result = []
    
    # EFFICIENT: No additional queries needed
    for post in posts:
        result.append({
            'post': post,
            'user': post.user  # Already loaded
        })
    
    return result

