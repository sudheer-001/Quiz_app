from django.db import models
import uuid
import random
from django.contrib.auth.models import User

class BaseModel(models.Model):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Category(BaseModel):
    category_name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.category_name

class Question(BaseModel):
    category = models.ForeignKey(Category, related_name='questions', on_delete=models.CASCADE)
    question = models.TextField()
    marks = models.IntegerField(default=1)
    def __str__(self):
        return self.question
    def get_answers(self):
        answer_objs = list(self.answer_set.all())
        random.shuffle(answer_objs)
        data = []
        for a in answer_objs:
            data.append({'uid': str(a.uid), 'answer': a.answer, 'is_correct': a.is_correct})
        return data

class Answer(BaseModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    def __str__(self):
        return self.answer

class Attempt(models.Model):
    user = models.ForeignKey(User, related_name="attempts", on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name="attempts", on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    total_marks = models.IntegerField(default=0)
    attempted_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.user.username} - {self.category} : {self.score}/{self.total_marks}"

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, blank=True)
    branch = models.CharField(max_length=100, blank=True)
    year = models.CharField(max_length=20, blank=True)
    contact = models.CharField(max_length=20, blank=True)
    enrollment = models.CharField(max_length=50, blank=True)
    def __str__(self):
        return f"{self.user.username} profile"
