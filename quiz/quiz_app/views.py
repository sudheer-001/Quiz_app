import json
import os
import subprocess
import random
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from .models import Category, Question, Answer, Attempt, StudentProfile
import logging
logger = logging.getLogger(__name__)

def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("register")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect("register")
        User.objects.create_user(username=username, email=email, password=password1)
        messages.success(request, "Registration successful. Please log in.")
        return redirect("login")
    return render(request, "quiz_app/register.html")

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password")
            return redirect("login")
    return render(request, "quiz_app/login.html")

def user_logout(request):
    logout(request)
    return redirect("login")

@login_required
def my_scores(request):
    attempts = Attempt.objects.filter(user=request.user).select_related("category").order_by("-attempted_at")
    context = {"attempts": attempts}
    return render(request, "quiz_app/scores.html", context)

def quiz_app(request):
    categories = Category.objects.all()
    return render(request, "quiz_app/index.html", {"categories": categories})

@login_required
def quiz_page(request):
    category = request.GET.get('category', '')
    level = request.GET.get('level', '')
    return render(request, "quiz_app/quiz.html", {"category": category, "level": level})

@login_required
def get_quiz(request):
    try:
        category_name = request.GET.get('category', '')
        count = int(request.GET.get('count', 10))
        qs = Question.objects.all()
        if category_name and category_name.upper() != "MIX":
            qs = qs.filter(category__category_name__iexact=category_name)
        qlist = list(qs)
        random.shuffle(qlist)
        qlist = qlist[:count]
        data = []
        for q in qlist:
            data.append({
                "uid": str(q.uid),
                "question": q.question,
                "marks": q.marks,
                "answers": q.get_answers(),
                "category": q.category.category_name
            })
        return JsonResponse({"status": True, "data": data})
    except Exception as e:
        return JsonResponse({"status": False, "message": str(e)}, status=500)

@login_required
@csrf_protect
def save_result(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "POST required"}, status=400)
    try:
        data = json.loads(request.body.decode("utf-8"))
        score = int(data.get("score", 0))
        total = int(data.get("total_marks", 0))
        category_name = data.get("category", "")
        category = Category.objects.filter(category_name__iexact=category_name).first()
        if not category:
            return JsonResponse({"status": False, "message": "Category not found"}, status=400)
        Attempt.objects.create(user=request.user, category=category, score=score, total_marks=total)
        profile = StudentProfile.objects.filter(user=request.user).first()
        enrollment = profile.enrollment if profile else ""
        file_path = os.path.join(settings.BASE_DIR, "quiz_results.txt")
        line = f"{enrollment}\t{category.category_name}\t{score}/{total}\t{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(line)
        return JsonResponse({"status": True})
    except Exception as e:
        return JsonResponse({"status": False, "message": str(e)}, status=500)

@csrf_exempt
def generate_questions(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "POST required"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except:
        data = {}

    category = data.get("category", "")
    difficulty = data.get("difficulty", "easy")
    count = int(data.get("count", 5))

    prompt = f"""
    Generate {count} multiple-choice questions for the category: {category}.
    Difficulty: {difficulty}.
    Format the output strictly as JSON list:
    [
      {{
        "question": "...",
        "options": ["A","B","C","D"],
        "correct": 1,
        "marks": 1
      }}
    ]
    No explanation.
    """

    try:
        result = subprocess.run(
            ["ollama", "run", "mistral"],
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=25
        )
    except subprocess.TimeoutExpired:
        return _fallback_questions(category, count, "Ollama timeout")

    stdout = (result.stdout or b"").decode("utf-8", errors="ignore").strip()
    stderr = (result.stderr or b"").decode("utf-8", errors="ignore").strip()
    ret = result.returncode

    if ret != 0 or not stdout:
        return _fallback_questions(category, count, f"Ollama error: code={ret} stderr={stderr[:500]}")

    try:
        ai_questions = json.loads(stdout)
        questions_out = []
        for q in ai_questions[:count]:
            opts = q.get("options") or q.get("answers") or []
            questions_out.append({
                "question": q.get("question",""),
                "answers": [
                    {"uid": i, "answer": str(o), "is_correct": (i==int(q.get("correct",0)) )} for i,o in enumerate(opts)
                ],
                "marks": int(q.get("marks",1))
            })
        return JsonResponse({"status": True, "questions": questions_out})
    except Exception as e:
        return _fallback_questions(category, count, f"Invalid AI JSON: {str(e)}. raw={stdout[:1000]}")

def _fallback_questions(category, count, reason):
    qs = Question.objects.filter(category__category_name__icontains=category)[:count]
    out = []
    for q in qs:
        ans_objs = list(q.answer_set.all())
        answers = []
        for i,a in enumerate(ans_objs):
            answers.append({"uid": i, "answer": a.answer, "is_correct": a.is_correct})
        out.append({"question": q.question, "answers": answers, "marks": q.marks})
    return JsonResponse({"status": False, "message": reason, "questions": out})


@login_required
def profile(request):
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile.full_name = request.POST.get("full_name", "")
        profile.branch = request.POST.get("branch", "")
        profile.year = request.POST.get("year", "")
        profile.contact = request.POST.get("contact", "")
        profile.enrollment = request.POST.get("enrollment", "")
        request.user.first_name = profile.full_name
        request.user.email = request.POST.get("email", request.user.email)
        request.user.save()
        profile.save()
        messages.success(request, "Profile updated")
        return redirect("profile")
    return render(request, "quiz_app/profile.html", {"profile": profile})

