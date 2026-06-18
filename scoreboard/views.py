from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import Match


@login_required
def home(request):
    matches = Match.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'home.html', {'matches': matches})


@login_required
def create_match(request):
    if request.method == "POST":
        sport = request.POST['sport']
        team_a = request.POST['team_a']
        team_b = request.POST['team_b']

        Match.objects.create(
            user=request.user,
            sport_name=sport,
            team_a=team_a,
            team_b=team_b,
        )
        return redirect('home')

    return render(request, 'create_match.html')


@login_required
def update_score(request, match_id, team):
    match = get_object_or_404(Match, id=match_id, user=request.user)

    if match.is_ended:
        return redirect('home')

    if team == "A":
        match.score_a += 1
    elif team == "B":
        match.score_b += 1
    else:
        raise Http404("Invalid team")

    match.save(update_fields=["score_a", "score_b"]) 
    return redirect('home')


@login_required
def end_match(request, match_id):
    match = get_object_or_404(Match, id=match_id, user=request.user)

    if match.is_ended:
        return redirect('home')

    if match.score_a > match.score_b:
        match.winner = match.team_a
    elif match.score_b > match.score_a:
        match.winner = match.team_b
    else:
        match.winner = "Draw"

    match.is_ended = True
    match.save(update_fields=["winner", "is_ended"]) 
    return redirect('home')


@login_required
def history(request):
    matches = Match.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'history.html', {'matches': matches})

