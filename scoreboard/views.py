from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from .models import Match
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from cricket.models import CricketMatch, Player, Innings, Ball




@login_required
def home(request):
    matches = Match.objects.filter(user=request.user).order_by('-created_at') # type: ignore
    return render(request, 'home.html', {'matches': matches})


@login_required
def create_match(request): # type: ignore
    if request.method == "POST": # type: ignore
        sport = request.POST['sport'] # type: ignore
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

    sport = (match.sport_name or "").strip().lower()

    if sport == "basketball":
        points = 2
    elif sport == "tennis":
        points = 1
    else:
        # football, or any custom sport
        points = 1

    if team == "A":
        match.score_a += points
    elif team == "B":
        match.score_b += points
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


@login_required
def create_cricket_match(request):
    if request.method == "POST":
        match_type = request.POST.get('match_type')
        team_a_name = request.POST.get('team_a')
        team_b_name = request.POST.get('team_b')
        team_a_players = request.POST.getlist('team_a_players[]')
        team_b_players = request.POST.getlist('team_b_players[]')
        
        # Create match
        match = Match.objects.create(
            user=request.user,
            sport_name="cricket",
            team_a=team_a_name,
            team_b=team_b_name,
            # Save venue fields entered on the generic match creation page
            venue_stadium_name=request.POST.get('venue_stadium_name') or '',
            venue_city=request.POST.get('venue_city') or '',

        )

        
        # Create cricket match details
        cricket_match = CricketMatch.objects.create(
            match=match,
            match_type=match_type,  # 't20', 'odi', 'test'
            overs=20 if match_type == 't20' else (50 if match_type == 'odi' else None),
            is_limited_overs=(match_type != 'test')
        )
        
        # Create players for team A
        for player_name in team_a_players:
            if player_name.strip():
                Player.objects.create(
                    cricket_match=cricket_match,
                    name=player_name.strip(),
                    team='A'
                )
        
        # Create players for team B
        for player_name in team_b_players:
            if player_name.strip():
                Player.objects.create(
                    cricket_match=cricket_match,
                    name=player_name.strip(),
                    team='B'
                )
        
        # Create first innings
        Innings.objects.create(cricket_match=cricket_match, innings_number=1)
        
        return redirect('cricket_match_detail', match_id=match.id)
    
    return render(request, 'create_cricket_match.html')

@login_required
def cricket_match_detail(request, match_id):
    match = get_object_or_404(Match, id=match_id, user=request.user)
    cricket_match = get_object_or_404(CricketMatch, match=match)
    
    current_innings = cricket_match.innings.filter(is_completed=False).first()
    
    context = {
        'match': match,
        'cricket_match': cricket_match,
        'current_innings': current_innings,
        'team_a_players': cricket_match.players.filter(team='A'),
        'team_b_players': cricket_match.players.filter(team='B'),
        'all_innings': cricket_match.innings.all().order_by('innings_number'),
    }
    return render(request, 'cricket_match_detail.html', context)

@csrf_exempt
@login_required
@require_POST
def add_ball_score(request):
    try:
        data = json.loads(request.body)
        innings_id = data.get('innings_id')
        batsman_id = data.get('batsman_id')
        non_striker_id = data.get('non_striker_id')
        bowler_id = data.get('bowler_id')
        runs = int(data.get('runs', 0))
        extras = data.get('extras', 'none')  # 'none', 'wide', 'no_ball', 'bye', 'leg_bye'
        is_wicket = data.get('is_wicket', False)
        wicket_type = data.get('wicket_type', '')  # 'bowled', 'caught', 'lbw', 'run_out', 'stumped'
        fielder_id = data.get('fielder_id')
        
        innings = get_object_or_404(Innings, id=innings_id)
        cricket_match = innings.cricket_match
        
        # Check if match is over
        if cricket_match.match.is_ended:
            return JsonResponse({'error': 'Match already ended'}, status=400)
        
        # Check if innings is over
        if innings.is_completed:
            return JsonResponse({'error': 'Innings already completed'}, status=400)
        
        # Check overs limit for limited overs matches
        if cricket_match.is_limited_overs and innings.overs_bowled >= cricket_match.overs:
            innings.is_completed = True
            innings.save()
            
            # Check if second innings should start
            if innings.innings_number == 1:
                start_second_innings(cricket_match)
            else:
                end_cricket_match(cricket_match)
            
            return JsonResponse({'status': 'innings_completed', 'next_action': 'start_second_innings' if innings.innings_number == 1 else 'match_ended'})
        
        # Calculate runs to add
        runs_scored = runs
        if extras == 'wide' or extras == 'no_ball':
            runs_scored += 1  # extra ball counts as 1 run
        
        # Update innings totals
        innings.total_runs += runs_scored
        innings.balls_bowled += 1
        
        # Update overs
        if innings.balls_bowled % 6 == 0:
            innings.overs_bowled += 1
        
        # Update batsman stats
        batsman = get_object_or_404(Player, id=batsman_id)
        non_striker = get_object_or_404(Player, id=non_striker_id)
        bowler = get_object_or_404(Player, id=bowler_id)
        
        # Update batsman
        if is_wicket:
            batsman.is_out = True
            batsman.out_type = wicket_type
            batsman.out_to = bowler
            if fielder_id and wicket_type in ['caught', 'run_out', 'stumped']:
                batsman.out_by = get_object_or_404(Player, id=fielder_id)
        
        if runs > 0 and not is_wicket:
            batsman.runs_scored += runs
            if runs >= 4:
                batsman.fours += 1
            if runs >= 6:
                batsman.sixes += 1
        
        batsman.balls_faced += 1
        batsman.save()
        
        # Update non-striker
        if runs % 2 == 0 and runs > 0:
            # Change strike if odd number of runs (including extras)
            pass  # We'll swap later if needed
        
        # Update bowler
        if not extras in ['wide', 'no_ball']:  # Wides and no-balls don't count as legitimate balls
            bowler.balls_bowled += 1
        
        if is_wicket:
            bowler.wickets_taken += 1
        
        bowler.runs_conceded += runs_scored
        bowler.save()
        
        # Create ball record
        Ball.objects.create(
            innings=innings,
            batsman=batsman,
            non_striker=non_striker,
            bowler=bowler,
            runs=runs,
            extras=extras,
            is_wicket=is_wicket,
            wicket_type=wicket_type,
            fielder=fielder_id and get_object_or_404(Player, id=fielder_id)
        )
        
        # Swap batsmen if runs were odd
        if runs % 2 != 0:
            # Swap strike for next ball
            pass  # We'll handle this in the frontend by updating the UI
        
        innings.save()
        
        # Check for innings completion conditions
        if is_wicket and len(innings.cricket_match.players.filter(team=innings.team_batting, is_out=False)) <= 1:
            innings.is_completed = True
            innings.save()
            
            if innings.innings_number == 1:
                start_second_innings(cricket_match)
            else:
                end_cricket_match(cricket_match)
            
            return JsonResponse({'status': 'innings_completed'})
        
        return JsonResponse({
            'status': 'success',
            'total_runs': innings.total_runs,
            'overs': f"{innings.overs_bowled}.{innings.balls_bowled % 6}",
            'wickets': innings.cricket_match.players.filter(team=innings.team_batting, is_out=True).count(),
            'batsman_name': batsman.name,
            'batsman_runs': batsman.runs_scored,
            'batsman_balls': batsman.balls_faced,
            'bowler_name': bowler.name,
            'bowler_wickets': bowler.wickets_taken,
            'bowler_runs': bowler.runs_conceded,
            'striker_id': non_striker.id if runs % 2 != 0 else batsman.id,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def start_second_innings(cricket_match):
    # Create second innings
    first_innings = cricket_match.innings.get(innings_number=1)
    second_innings = Innings.objects.create(
        cricket_match=cricket_match,
        innings_number=2,
        team_batting='B',
        target_runs=first_innings.total_runs + 1
    )

def end_cricket_match(cricket_match):
    match = cricket_match.match
    innings1 = cricket_match.innings.get(innings_number=1)
    innings2 = cricket_match.innings.get(innings_number=2)
    
    if innings2.total_runs > innings1.total_runs:
        match.winner = match.team_b
    elif innings1.total_runs > innings2.total_runs:
        match.winner = match.team_a
    else:
        # In case of tie, check for super over (simplified)
        match.winner = "Tie"
    
    match.is_ended = True
    match.save(update_fields=["winner", "is_ended"])

@login_required
def cricket_scoreboard(request, match_id):
    match = get_object_or_404(Match, id=match_id, user=request.user)
    cricket_match = get_object_or_404(CricketMatch, match=match)
    
    innings_data = []
    for innings in cricket_match.innings.all().order_by('innings_number'):
        balls = innings.balls.all()
        batsmen_stats = []
        bowlers_stats = []
        
        # Get batsmen stats
        for player in innings.cricket_match.players.filter(team=innings.team_batting):
            batsmen_stats.append({
                'name': player.name,
                'runs': player.runs_scored,
                'balls': player.balls_faced,
                'fours': player.fours,
                'sixes': player.sixes,
                'is_out': player.is_out,
                'out_type': player.out_type
            })
        
        # Get bowlers stats
        for player in innings.cricket_match.players.filter(team='A' if innings.team_batting == 'B' else 'B'):
            bowlers_stats.append({
                'name': player.name,
                'overs': f"{player.balls_bowled // 6}.{player.balls_bowled % 6}",
                'maidens': 0,  # To be calculated
                'runs': player.runs_conceded,
                'wickets': player.wickets_taken
            })
        
        innings_data.append({
            'number': innings.innings_number,
            'team': innings.team_batting,
            'total_runs': innings.total_runs,
            'overs': f"{innings.overs_bowled}.{innings.balls_bowled % 6}",
            'wickets': innings.cricket_match.players.filter(team=innings.team_batting, is_out=True).count(),
            'target_runs': innings.target_runs,
            'is_completed': innings.is_completed,
            'batsmen': batsmen_stats,
            'bowlers': bowlers_stats,
            'balls': balls
        })
    
    context = {
        'match': match,
        'cricket_match': cricket_match,
        'innings_data': innings_data,
    }
    return render(request, 'cricket_scoreboard.html', context)

@login_required
def update_cricket_score(request, match_id):
    # Legacy endpoint - redirect to new system
    return redirect('cricket_match_detail', match_id=match_id)
