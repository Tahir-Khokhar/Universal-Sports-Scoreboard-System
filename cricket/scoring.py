"""Real-world cricket scoring helpers."""

from .models import Player


def format_overs(legal_balls: int) -> str:
    return f"{legal_balls // 6}.{legal_balls % 6}"


def wickets_fallen(cricket_match, team_batting: str) -> int:
    return cricket_match.players.filter(team=team_batting, is_out=True).count()


def batting_team_name(match, team_code: str) -> str:
    return match.team_a if team_code == 'A' else match.team_b


def bowling_team_code(batting_team: str) -> str:
    return 'B' if batting_team == 'A' else 'A'


def not_out_batsmen_count(cricket_match, team_batting: str) -> int:
    return cricket_match.players.filter(team=team_batting, is_out=False).count()


def innings_limit_reached(innings, cricket_match) -> bool:
    if not cricket_match.is_limited_overs or cricket_match.overs is None:
        return False
    return innings.balls_bowled >= cricket_match.overs * 6


def all_out(innings, cricket_match) -> bool:
    return wickets_fallen(cricket_match, innings.team_batting) >= 10


def calculate_runs(extras: str, runs: int) -> int:
    if extras == 'wide':
        return 1 + runs
    if extras == 'no_ball':
        return 1 + runs
    return runs


def is_legal_delivery(extras: str) -> bool:
    return extras not in ('wide', 'no_ball')


def batsman_faces_ball(extras: str, is_wicket: bool, wicket_type: str) -> bool:
    if extras in ('wide', 'bye', 'leg_bye'):
        return False
    if is_wicket and wicket_type == 'run_out':
        return False
    return True


def batsman_gets_runs(extras: str, runs: int) -> bool:
    return extras == 'none' and runs > 0


def should_rotate_strike(runs: int, legal_ball: bool, legal_balls_after: int) -> bool:
    """Standard cricket strike rotation:
    - Rotate if batsman scored odd runs (1, 3, etc. - represent physical runs).
    - Rotate if the over ended (legal ball and balls bowled is multiple of 6).
    - If both happen, they cancel out, so they don't rotate.
    """
    runs_odd = (runs % 2 == 1)
    over_ended = (legal_ball and legal_balls_after > 0 and legal_balls_after % 6 == 0)
    return runs_odd ^ over_ended


def swap_striker(batsman, non_striker):
    return non_striker, batsman


def get_balls_in_current_over(innings, bowler=None):
    """Get all balls in the current over for a given innings."""
    balls = list(innings.balls.order_by('-ball_number'))
    
    # Count backwards to find balls in current over (last 6 legal deliveries)
    over_balls = []
    legal_count = 0
    
    for b in balls:
        over_balls.append(b)
        if b.extras not in ('wide', 'no_ball'):
            legal_count += 1
        if legal_count == 6:
            break
    
    # If bowler is specified, filter by bowler
    if bowler:
        over_balls = [b for b in over_balls if b.bowler.id == bowler.id]
    
    return over_balls


def check_and_update_maiden(innings, bowler) -> bool:
    """Check if the last completed over was a maiden and update bowler stats if so."""
    balls = list(innings.balls.order_by('-ball_number'))
    
    # We count backwards to find the balls belonging to the current over.
    # An over ends when we reach 6 legal deliveries.
    over_balls = []
    legal_count = 0
    for b in balls:
        over_balls.append(b)
        if b.extras not in ('wide', 'no_ball'):
            legal_count += 1
        if legal_count == 6:
            break
            
    if legal_count < 6:
        return False
        
    # Check if any runs were conceded in these balls.
    total_conceded = 0
    for b in over_balls:
        if b.extras == 'wide':
            total_conceded += 1 + b.runs
        elif b.extras == 'no_ball':
            total_conceded += 1 + b.runs
        elif b.extras == 'none':
            total_conceded += b.runs
            
    if total_conceded == 0:
        bowler.maidens += 1
        bowler.save(update_fields=['maidens'])
        return True
    return False


def get_current_batsmen(innings, cricket_match):
    """Determine the current striker and non-striker based on the last ball bowled."""
    last_ball = innings.balls.order_by('-ball_number', '-created_at').first()
    batting_team = innings.team_batting
    
    # Get all available not-out batters
    not_out = list(cricket_match.players.filter(team=batting_team, is_out=False).order_by('batting_order', 'id'))
    
    if not last_ball:
        striker = not_out[0] if len(not_out) >= 1 else None
        non_striker = not_out[1] if len(not_out) >= 2 else None
        return striker, non_striker

    striker = last_ball.batsman
    non_striker = last_ball.non_striker
    
    # If any player got out, they need replacement
    if striker.is_out or non_striker.is_out:
        active_ids = []
        if not striker.is_out:
            active_ids.append(striker.id)
        if not non_striker.is_out:
            active_ids.append(non_striker.id)
            
        remaining = [p for p in not_out if p.id not in active_ids]
        
        if striker.is_out:
            striker = remaining[0] if len(remaining) >= 1 else None
        if non_striker.is_out:
            non_striker = remaining[0] if len(remaining) >= 1 else None
            
        return striker, non_striker
        
    # If neither is out, check strike rotation
    runs = last_ball.runs
    legal_ball = is_legal_delivery(last_ball.extras)
    
    if should_rotate_strike(runs, legal_ball, innings.balls_bowled):
        striker, non_striker = non_striker, striker
        
    return striker, non_striker


def update_boundary_stats(batsman, runs: int):
    if runs == 4:
        batsman.fours += 1
    elif runs == 6:
        batsman.sixes += 1


def record_ball(match_id, ball_data):
    """
    Record a ball in the match.
    
    Args:
        match_id: ID of the CricketMatch
        ball_data: Dictionary containing ball information
    
    Returns:
        dict: Updated match state information
    """
    from django.db import transaction
    from .models import CricketMatch, Ball, Innings
    
    with transaction.atomic():
        # Get the match
        cricket_match = CricketMatch.objects.get(id=match_id)
        
        # Get or create the current innings
        innings = Innings.objects.filter(
            cricket_match=cricket_match,
            is_completed=False
        ).first()
        
        if not innings:
            # Start a new innings
            innings_count = Innings.objects.filter(cricket_match=cricket_match).count()
            innings = Innings.objects.create(
                cricket_match=cricket_match,
                innings_number=innings_count + 1,
                team_batting=ball_data.get('batting_team', 'A')
            )
        
        # Create the ball
        ball = Ball.objects.create(
            innings=innings,
            batsman_id=ball_data['batsman_id'],
            non_striker_id=ball_data['non_striker_id'],
            bowler_id=ball_data['bowler_id'],
            runs=ball_data.get('runs', 0),
            extras=ball_data.get('extras', 'none'),
            is_wicket=ball_data.get('is_wicket', False),
            wicket_type=ball_data.get('wicket_type', ''),
            fielder_id=ball_data.get('fielder_id'),
            ball_number=innings.balls.count() + 1
        )
        
        # Update innings stats
        if is_legal_delivery(ball.extras):
            innings.balls_bowled += 1
            if innings.balls_bowled % 6 == 0:
                innings.overs_bowled += 1
        
        # Update runs
        total_runs = calculate_runs(ball.extras, ball.runs)
        innings.total_runs += total_runs
        
        # Update innings target if completed
        if innings.balls_bowled >= cricket_match.overs * 6 or all_out(innings, cricket_match):
            innings.is_completed = True
            innings.target_runs = innings.total_runs + 1  # Target is runs + 1
        
        innings.save()
        
        # Update player stats
        batsman = ball.batsman
        bowler = ball.bowler
        
        # Update batsman stats
        if batsman_faces_ball(ball.extras, ball.is_wicket, ball.wicket_type):
            batsman.balls_faced += 1
        
        if ball.is_wicket:
            batsman.is_out = True
            batsman.out_type = ball.wicket_type
            if ball.fielder:
                batsman.out_to = ball.batsman
                batsman.out_by = ball.fielder
        
        # Update runs for batsman (excluding extras)
        if batsman_gets_runs(ball.extras, ball.runs):
            batsman.runs_scored += ball.runs
            update_boundary_stats(batsman, ball.runs)
        
        # Update bowler stats
        if is_legal_delivery(ball.extras):
            bowler.balls_bowled += 1
            
        # Update runs conceded by bowler
        if ball.extras in ('wide', 'no_ball'):
            bowler.runs_conceded += 1
        if ball.extras != 'bye' and ball.extras != 'leg_bye':
            bowler.runs_conceded += ball.runs
            
        if ball.is_wicket and ball.wicket_type in ('bowled', 'lbw', 'caught', 'stumped'):
            bowler.wickets_taken += 1
        
        batsman.save()
        bowler.save()
        
        # Check for maiden over
        over_balls = get_balls_in_current_over(innings, bowler)
        runs_conceded_this_over = sum([
            calculate_runs(b.extras, b.runs) for b in over_balls
        ])
        
        if len(over_balls) == 6 and runs_conceded_this_over == 0:
            bowler.maidens += 1
            bowler.save(update_fields=['maidens'])
        
        # Update non-striker if not out
        if ball.is_wicket and ball.batsman.is_out:
            # Find next batsman
            next_batsman = cricket_match.players.filter(
                team=innings.team_batting,
                is_out=False
            ).exclude(id__in=[ball.non_striker.id]).order_by('batting_order').first()
            
            if next_batsman:
                ball.non_striker = next_batsman
        
        # Return updated match state
        return {
            'ball': ball_display(ball),
            'runs': innings.total_runs,
            'overs': format_overs(innings.balls_bowled),
            'wickets': wickets_fallen(cricket_match, innings.team_batting),
            'is_completed': innings.is_completed
        }


def serialize_player(player: Player) -> dict:
    return {
        'id': player.id,
        'name': player.name,
        'team': player.team,
        'runs': player.runs_scored,
        'balls': player.balls_faced,
        'fours': player.fours,
        'sixes': player.sixes,
        'is_out': player.is_out,
        'out_type': player.out_type or '',
        'wickets': player.wickets_taken,
        'runs_conceded': player.runs_conceded,
        'balls_bowled': player.balls_bowled,
        'overs': format_overs(player.balls_bowled),
        'maidens': player.maidens,
        'batting_order': player.batting_order,
        'batting_category': player.get_batting_category_display(),
        'bowling_role': player.get_player_role_display(),  # Updated to match new field name
    }


def ball_display(ball) -> str:
    if ball.is_wicket:
        return 'W'
    if ball.extras == 'wide':
        return f"Wd+{ball.runs}" if ball.runs else 'Wd'
    if ball.extras == 'no_ball':
        return f"Nb+{ball.runs}" if ball.runs else 'Nb'
    if ball.extras == 'bye':
        return f"B{ball.runs}" if ball.runs else 'B'
    if ball.extras == 'leg_bye':
        return f"Lb{ball.runs}" if ball.runs else 'Lb'
    return str(ball.runs)
