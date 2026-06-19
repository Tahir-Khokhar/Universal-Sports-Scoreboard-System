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


def should_rotate_strike(runs_scored: int, legal_ball: bool, legal_balls_after: int) -> bool:
    """Standard cricket strike rotation:
    - Swap ends on odd runs off the bat (wides/no-balls are handled upstream by giving legal_ball). 
    - Also swap at the end of an over (after the 6th legal ball), even if total is even.

    Note: caller passes `runs_scored` as runs added to the batting team's score.
    """
    if legal_ball and legal_balls_after > 0 and legal_balls_after % 6 == 0:
        return True
    # odd runs (1,3,5,...) cause strike change on a legal ball
    return (runs_scored % 2) == 1



def swap_striker(batsman, non_striker):
    return non_striker, batsman


def update_boundary_stats(batsman, runs: int):
    if runs == 4:
        batsman.fours += 1
    elif runs == 6:
        batsman.sixes += 1


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
