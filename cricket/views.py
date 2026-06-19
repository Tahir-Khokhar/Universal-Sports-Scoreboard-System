import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from scoreboard.models import Match
from .models import CricketMatch, Player, Innings, Ball
from . import scoring as cs


def _get_cricket_match(request, match_id):
    match = get_object_or_404(Match, id=match_id, user=request.user)
    cricket_match = get_object_or_404(CricketMatch, match=match)
    return match, cricket_match


def _toss_done(request, match_id, cricket_match):
    if request.session.get(f"cricket_toss_{match_id}"):
        return True
    first_innings = cricket_match.innings.filter(innings_number=1).first()
    return bool(first_innings and first_innings.balls_bowled > 0)


def start_second_innings(cricket_match):
    first_innings = cricket_match.innings.get(innings_number=1)
    second_batting = 'B' if first_innings.team_batting == 'A' else 'A'
    Innings.objects.create(
        cricket_match=cricket_match,
        innings_number=2,
        team_batting=second_batting,
        target_runs=first_innings.total_runs + 1,
    )


def end_cricket_match(cricket_match):
    match = cricket_match.match
    innings1 = cricket_match.innings.get(innings_number=1)
    innings2 = cricket_match.innings.get(innings_number=2)

    team1_name = cs.batting_team_name(match, innings1.team_batting)
    team2_name = cs.batting_team_name(match, innings2.team_batting)

    if innings2.total_runs > innings1.total_runs:
        match.winner = team2_name
    elif innings1.total_runs > innings2.total_runs:
        match.winner = team1_name
    else:
        match.winner = "Tie"

    match.score_a = innings2.total_runs if innings1.team_batting == 'B' else innings1.total_runs
    match.score_b = innings1.total_runs if innings1.team_batting == 'B' else innings2.total_runs
    match.is_ended = True
    match.save(update_fields=["winner", "score_a", "score_b", "is_ended"])


def complete_innings(innings, cricket_match):
    innings.is_completed = True
    innings.save(update_fields=['is_completed'])
    if innings.innings_number == 1:
        start_second_innings(cricket_match)
        return 'innings_completed', 'second_innings_started'
    end_cricket_match(cricket_match)
    return 'match_completed', 'match_ended'


def build_match_state(match, cricket_match, current_innings=None, toss_data=None):
    if current_innings is None:
        current_innings = cricket_match.innings.filter(is_completed=False).order_by('innings_number').first()

    innings_list = []
    for innings in cricket_match.innings.all().order_by('innings_number'):
        batting_name = cs.batting_team_name(match, innings.team_batting)
        bowling_code = cs.bowling_team_code(innings.team_batting)
        wickets = cs.wickets_fallen(cricket_match, innings.team_batting)

        batsmen = [
            cs.serialize_player(p)
            for p in cricket_match.players.filter(team=innings.team_batting).order_by('name')
        ]
        bowlers = [
            cs.serialize_player(p)
            for p in cricket_match.players.filter(team=bowling_code).order_by('name')
        ]
        recent_balls = [
            {
                'display': cs.ball_display(b),
                'is_wicket': b.is_wicket,
                'extras': b.extras,
            }
            for b in innings.balls.order_by('-created_at')[:12]
        ]

        run_rate = None
        required_rate = None
        legal_balls = innings.balls_bowled
        if legal_balls > 0:
            run_rate = round(innings.total_runs / (legal_balls / 6), 2)

        if innings.innings_number == 2 and innings.target_runs and cricket_match.overs:
            balls_remaining = max(cricket_match.overs * 6 - legal_balls, 0)
            runs_needed = max(innings.target_runs - innings.total_runs, 0)
            if balls_remaining > 0:
                required_rate = round(runs_needed / (balls_remaining / 6), 2)

        innings_list.append({
            'id': innings.id,
            'number': innings.innings_number,
            'team_code': innings.team_batting,
            'team_name': batting_name,
            'total_runs': innings.total_runs,
            'wickets': wickets,
            'overs': cs.format_overs(innings.balls_bowled),
            'target': innings.target_runs,
            'is_completed': innings.is_completed,
            'run_rate': run_rate,
            'required_rate': required_rate,
            'batsmen': batsmen,
            'bowlers': bowlers,
            'recent_balls': list(reversed(recent_balls)),
        })

    current_data = None
    if current_innings:
        batting_code = current_innings.team_batting
        bowling_code = cs.bowling_team_code(batting_code)
        current_data = {
            'id': current_innings.id,
            'number': current_innings.innings_number,
            'batting_team_code': batting_code,
            'batting_team_name': cs.batting_team_name(match, batting_code),
            'bowling_team_code': bowling_code,
            'bowling_team_name': cs.batting_team_name(match, bowling_code),
            'total_runs': current_innings.total_runs,
            'wickets': cs.wickets_fallen(cricket_match, batting_code),
            'overs': cs.format_overs(current_innings.balls_bowled),
            'max_overs': cricket_match.overs,
            'target': current_innings.target_runs,
            'batting_players': [
                cs.serialize_player(p)
                for p in cricket_match.players.filter(team=batting_code, is_out=False).order_by('batting_order', 'name')
            ],

            'bowling_players': [
                cs.serialize_player(p)
                for p in cricket_match.players.filter(team=bowling_code).order_by('name')
            ],
            'all_batting_players': [
                cs.serialize_player(p)
                for p in cricket_match.players.filter(team=batting_code).order_by('batting_order', 'name')
            ],

        }

    return {
        'match_id': match.id,
        'team_a': match.team_a,
        'team_b': match.team_b,
        'match_type': cricket_match.get_match_type_display(),
        'is_ended': match.is_ended,
        'winner': match.winner,
        'current_innings': current_data,
        'innings': innings_list,
        'toss': toss_data,
    }


@login_required
def create_cricket_match(request):
    if request.method == "POST":
        match_type = request.POST.get('match_type')
        team_a_name = request.POST.get('team_a')
        team_b_name = request.POST.get('team_b')
        team_a_players = request.POST.getlist('team_a_players[]')
        team_b_players = request.POST.getlist('team_b_players[]')

        match = Match.objects.create(
            user=request.user,
            sport_name="cricket",
            team_a=team_a_name,
            team_b=team_b_name,
        )

        cricket_match = CricketMatch.objects.create(
            match=match,
            match_type=match_type,
            overs=20 if match_type == 't20' else (50 if match_type == 'odi' else None),
            is_limited_overs=(match_type != 'test'),
        )

        for player_name in team_a_players:
            if player_name.strip():
                Player.objects.create(cricket_match=cricket_match, name=player_name.strip(), team='A')

        for player_name in team_b_players:
            if player_name.strip():
                Player.objects.create(cricket_match=cricket_match, name=player_name.strip(), team='B')

        Innings.objects.create(cricket_match=cricket_match, innings_number=1)
        return redirect('cricket_toss', match_id=match.id)

    return render(request, 'create_cricket_match.html')


@login_required
def cricket_toss(request, match_id):
    match, cricket_match = _get_cricket_match(request, match_id)
    if _toss_done(request, match_id, cricket_match):
        return redirect('cricket_match_detail', match_id=match.id)

    return render(request, 'cricket_toss.html', {
        'match': match,
        'cricket_match': cricket_match,
    })


@login_required
@require_POST
def save_cricket_toss(request, match_id):
    match, cricket_match = _get_cricket_match(request, match_id)

    try:
        payload = json.loads(request.body)
        toss_winner = payload.get('toss_winner')
        decision = payload.get('decision')

        if toss_winner not in ('A', 'B'):
            return JsonResponse({'error': 'Invalid toss winner'}, status=400)
        if decision not in ('bat', 'bowl'):
            return JsonResponse({'error': 'Invalid decision'}, status=400)

        batting_team = toss_winner if decision == 'bat' else cs.bowling_team_code(toss_winner)

        first_innings = cricket_match.innings.get(innings_number=1)
        first_innings.team_batting = batting_team
        first_innings.save(update_fields=['team_batting'])

        toss_data = {
            'toss_winner': toss_winner,
            'toss_winner_name': cs.batting_team_name(match, toss_winner),
            'decision': decision,
            'batting_team': batting_team,
            'batting_team_name': cs.batting_team_name(match, batting_team),
        }
        request.session[f"cricket_toss_{match_id}"] = toss_data
        request.session.modified = True

        return JsonResponse({'status': 'success', 'toss': toss_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def cricket_match_detail(request, match_id):
    match, cricket_match = _get_cricket_match(request, match_id)

    if not _toss_done(request, match_id, cricket_match):
        return redirect('cricket_toss', match_id=match.id)

    current_innings = cricket_match.innings.filter(is_completed=False).order_by('innings_number').first()
    toss_data = request.session.get(f"cricket_toss_{match_id}", {})

    context = {
        'match': match,
        'cricket_match': cricket_match,
        'current_innings': current_innings,
        'toss_data': toss_data,
        'match_state_json': json.dumps(build_match_state(match, cricket_match, current_innings, toss_data)),
    }
    return render(request, 'cricket_match_detail.html', context)


@login_required
@require_GET
def get_match_state(request, match_id):
    match, cricket_match = _get_cricket_match(request, match_id)
    return JsonResponse(build_match_state(match, cricket_match, toss_data=request.session.get(f"cricket_toss_{match_id}")))


@login_required
@require_POST
def add_ball_score(request, match_id):
    try:
        payload = json.loads(request.body)

        innings_id = payload.get('innings_id')
        batsman_id = payload.get('batsman_id')
        non_striker_id = payload.get('non_striker_id')
        bowler_id = payload.get('bowler_id')

        runs = int(payload.get('runs', 0))
        extras = payload.get('extras', 'none')
        is_wicket = payload.get('is_wicket', False)
        wicket_type = payload.get('wicket_type', '')
        fielder_id = payload.get('fielder_id')

        innings = get_object_or_404(Innings, id=innings_id, cricket_match__match_id=match_id)
        cricket_match = innings.cricket_match
        match = cricket_match.match

        if match.is_ended:
            return JsonResponse({'error': 'Match already ended'}, status=400)
        if innings.is_completed:
            return JsonResponse({'error': 'Innings already completed'}, status=400)
        if cs.innings_limit_reached(innings, cricket_match):
            status, _ = complete_innings(innings, cricket_match)
            return JsonResponse({'status': status, 'state': build_match_state(match, cricket_match)})

        batsman = get_object_or_404(Player, id=batsman_id, cricket_match=cricket_match)
        non_striker = get_object_or_404(Player, id=non_striker_id, cricket_match=cricket_match)
        bowler = get_object_or_404(Player, id=bowler_id, cricket_match=cricket_match)

        if batsman.team != innings.team_batting or non_striker.team != innings.team_batting:
            return JsonResponse({'error': 'Batsmen must be from batting team'}, status=400)
        if bowler.team == innings.team_batting:
            return JsonResponse({'error': 'Bowler must be from bowling team'}, status=400)
        if batsman.is_out or non_striker.is_out:
            return JsonResponse({'error': 'Selected batsman is out'}, status=400)

        runs_scored = cs.calculate_runs(extras, runs)
        legal_ball = cs.is_legal_delivery(extras)

        innings.total_runs += runs_scored
        if legal_ball:
            innings.balls_bowled += 1
            innings.overs_bowled = innings.balls_bowled // 6

        faces_ball = cs.batsman_faces_ball(extras, is_wicket, wicket_type)
        if faces_ball:
            batsman.balls_faced += 1

        if cs.batsman_gets_runs(extras, runs):
            batsman.runs_scored += runs
            cs.update_boundary_stats(batsman, runs)

        fielder = None
        if is_wicket:
            batsman.is_out = True
            batsman.out_type = wicket_type
            batsman.out_to = bowler
            if fielder_id and wicket_type in ['caught', 'run_out', 'stumped']:
                fielder = get_object_or_404(Player, id=fielder_id, cricket_match=cricket_match)
                batsman.out_by = fielder

        batsman.save()

        if legal_ball:
            bowler.balls_bowled += 1
        bowler.runs_conceded += runs_scored
        if is_wicket:
            bowler.wickets_taken += 1
        bowler.save()

        ball_number = innings.balls.order_by('-ball_number').values_list('ball_number', flat=True).first() or 0
        Ball.objects.create(
            innings=innings,
            batsman=batsman,
            non_striker=non_striker,
            bowler=bowler,
            runs=runs,
            extras=extras,
            is_wicket=is_wicket,
            wicket_type=wicket_type,
            fielder=fielder,
            ball_number=ball_number + 1,
        )

        innings.save()

        new_striker = batsman
        new_non_striker = non_striker
        if cs.should_rotate_strike(runs_scored, legal_ball, innings.balls_bowled):
            new_striker, new_non_striker = cs.swap_striker(batsman, non_striker)

        # On wicket, bring next batter automatically based on batting order.
        if is_wicket:
            # If the striker got out, replace striker; otherwise replace non-striker.
            out_batter = batsman if faces_ball else None
            if out_batter is None:
                # fallback: if batsman.is_out set, assume striker
                out_batter = batsman

            batting_team = innings.team_batting

            def pick_next_batter(exclude_ids):
                # next batter = lowest batting_order among not-out players, excluding current ones
                qs = cricket_match.players.filter(team=batting_team, is_out=False).exclude(id__in=exclude_ids)
                return qs.order_by('batting_order', 'id').first()

            if batsman.id == (new_striker.id if new_striker else None):
                # striker was out; striker becomes next
                next_batter = pick_next_batter(exclude_ids=[batsman.id, non_striker.id])
                new_striker = next_batter
            else:
                # non-striker was out (e.g., run out); replace non-striker
                next_batter = pick_next_batter(exclude_ids=[batsman.id, non_striker.id])
                new_non_striker = next_batter


        if cs.all_out(innings, cricket_match) or cs.innings_limit_reached(innings, cricket_match):
            status, _ = complete_innings(innings, cricket_match)
            return JsonResponse({
                'status': status,
                'striker_id': new_striker.id if new_striker else None,
                'non_striker_id': new_non_striker.id if new_non_striker else None,
                'state': build_match_state(match, cricket_match),
            })

        return JsonResponse({
            'status': 'success',
            'runs_scored': runs_scored,
            'striker_id': new_striker.id if new_striker else None,
            'non_striker_id': new_non_striker.id if new_non_striker else None,
            'state': build_match_state(match, cricket_match),
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def cricket_scoreboard(request, match_id):
    match, cricket_match = _get_cricket_match(request, match_id)
    state = build_match_state(match, cricket_match, toss_data=toss_data)
    toss_data = request.session.get(f"cricket_toss_{match_id}", {})

    return render(request, 'cricket_scoreboard.html', {
        'match': match,
        'cricket_match': cricket_match,
        'state': state,
        'toss_data': toss_data,
    })
