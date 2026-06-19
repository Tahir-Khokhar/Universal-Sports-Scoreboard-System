/**
 * Live cricket scoring controller
 */
class CricketScorer {
  constructor(config) {
    this.matchId = config.matchId;
    this.scoreUrl = config.scoreUrl;
    this.stateUrl = config.stateUrl;
    this.csrfToken = config.csrfToken;
    this.state = config.initialState;

    this.strikerId = null;
    this.nonStrikerId = null;
    this.bowlerId = null;

    this.bindElements();
    this.bindEvents();
    this.render();
  }

  bindElements() {
    this.el = {
      scoreMain: document.getElementById('scoreMain'),
      scoreMeta: document.getElementById('scoreMeta'),
      scoreTeams: document.getElementById('scoreTeams'),
      runRate: document.getElementById('runRate'),
      requiredRate: document.getElementById('requiredRate'),
      targetDisplay: document.getElementById('targetDisplay'),
      recentBalls: document.getElementById('recentBalls'),
      battingTable: document.getElementById('battingTable'),
      bowlingTable: document.getElementById('bowlingTable'),
      strikerSelect: document.getElementById('strikerSelect'),
      nonStrikerSelect: document.getElementById('nonStrikerSelect'),
      bowlerSelect: document.getElementById('bowlerSelect'),
      runButtons: document.getElementById('runButtons'),
      matchEnded: document.getElementById('matchEnded'),
      scoringPanel: document.getElementById('scoringPanel'),
      inningsLabel: document.getElementById('inningsLabel'),
      fielderSelect: document.getElementById('fielderSelect'),
      fielderGroup: document.getElementById('fielderGroup'),
    };
  }

  bindEvents() {
    if (this.el.strikerSelect) {
      this.el.strikerSelect.addEventListener('change', () => this.onPlayerChange());
      this.el.nonStrikerSelect.addEventListener('change', () => this.onPlayerChange());
      this.el.bowlerSelect.addEventListener('change', () => {
        this.bowlerId = parseInt(this.el.bowlerSelect.value) || null;
      });
    }

    if (this.el.runButtons) {
      this.el.runButtons.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn || btn.disabled) return;
        const action = btn.dataset.action;
        if (action === 'wicket') {
          this.showWicketModal();
        } else {
          this.recordBall(action);
        }
      });
    }

    document.querySelectorAll('[data-wicket-type]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('[data-wicket-type]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const needsFielder = ['caught', 'run_out', 'stumped'].includes(btn.dataset.wicketType);
        if (this.el.fielderGroup) {
          this.el.fielderGroup.style.display = needsFielder ? 'block' : 'none';
        }
      });
    });

    const confirmWicket = document.getElementById('confirmWicket');
    if (confirmWicket) {
      confirmWicket.addEventListener('click', () => this.confirmWicket());
    }
  }

  onPlayerChange() {
    this.strikerId = parseInt(this.el.strikerSelect.value) || null;
    this.nonStrikerId = parseInt(this.el.nonStrikerSelect.value) || null;
    if (this.strikerId === this.nonStrikerId) {
      this.nonStrikerId = null;
      this.el.nonStrikerSelect.value = '';
    }
  }

  getCurrentInnings() {
    return this.state.current_innings;
  }

  canScore() {
    const inn = this.getCurrentInnings();
    return inn && !this.state.is_ended && this.strikerId && this.nonStrikerId && this.bowlerId;
  }

  render() {
    const inn = this.getCurrentInnings();
    const currentInningsData = this.state.innings.find(i => inn && i.id === inn.id);

    if (this.state.is_ended) {
      if (this.el.matchEnded) {
        this.el.matchEnded.style.display = 'block';
        this.el.matchEnded.textContent = `Match Over — Winner: ${this.state.winner}`;
      }
      if (this.el.scoringPanel) this.el.scoringPanel.style.display = 'none';
    }

    if (!inn) {
      if (this.el.scoreMain) this.el.scoreMain.textContent = '—';
      return;
    }

    if (this.el.scoreTeams) {
      this.el.scoreTeams.textContent = `${inn.batting_team_name} vs ${inn.bowling_team_name}`;
    }
    if (this.el.scoreMain) {
      this.el.scoreMain.textContent = `${inn.total_runs}/${inn.wickets}`;
    }
    if (this.el.scoreMeta) {
      this.el.scoreMeta.textContent = `(${inn.overs} overs)`;
    }
    if (this.el.inningsLabel) {
      const label = inn.number === 2 && inn.target
        ? `Innings ${inn.number} — Target: ${inn.target}`
        : `Innings ${inn.number}`;
      this.el.inningsLabel.textContent = label;
    }
    if (this.el.runRate && currentInningsData) {
      this.el.runRate.textContent = currentInningsData.run_rate ?? '—';
    }
    if (this.el.requiredRate && currentInningsData) {
      const rr = currentInningsData.required_rate;
      this.el.requiredRate.textContent = rr ?? '—';
      if (this.el.targetDisplay) {
        this.el.targetDisplay.style.display = inn.target ? 'block' : 'none';
      }
    }

    this.renderRecentBalls(currentInningsData);
    this.renderPlayerSelects(inn);
    this.renderStatsTables(currentInningsData);
    this.updateButtonState();
  }

  renderRecentBalls(inningsData) {
    if (!this.el.recentBalls || !inningsData) return;
    this.el.recentBalls.innerHTML = '';
    const balls = inningsData.recent_balls || [];
    balls.forEach((ball, idx) => {
      const chip = document.createElement('div');
      chip.className = 'ball-chip';
      if (ball.is_wicket) chip.classList.add('wicket');
      else if (ball.extras !== 'none') chip.classList.add('extra');
      else if (['4', '6'].includes(ball.display)) chip.classList.add('boundary');
      if (idx === balls.length - 1) chip.classList.add('latest');
      chip.textContent = ball.display;
      this.el.recentBalls.appendChild(chip);
    });
  }

  renderPlayerSelects(inn) {
    if (!this.el.strikerSelect) return;

    const fillSelect = (select, players, excludeId) => {
      const current = parseInt(select.value) || null;
      select.innerHTML = '<option value="">Select player</option>';
      players.forEach(p => {
        if (p.id === excludeId) return;
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.runs}${p.is_out ? ' — OUT' : ''})`;
        if (p.is_out) opt.disabled = true;
        select.appendChild(opt);
      });
      if (current && players.find(p => p.id === current && !p.is_out)) {
        select.value = current;
      }
    };

    fillSelect(this.el.strikerSelect, inn.batting_players, this.nonStrikerId);
    fillSelect(this.el.nonStrikerSelect, inn.batting_players, this.strikerId);
    fillSelect(this.el.bowlerSelect, inn.bowling_players, null);

    if (this.el.fielderSelect) {
      fillSelect(this.el.fielderSelect, inn.bowling_players, null);
    }

    this.strikerId = parseInt(this.el.strikerSelect.value) || this.strikerId;
    this.nonStrikerId = parseInt(this.el.nonStrikerSelect.value) || this.nonStrikerId;
    this.bowlerId = parseInt(this.el.bowlerSelect.value) || this.bowlerId;

    if (!this.strikerId && inn.batting_players.length >= 1) {
      const available = inn.batting_players.filter(p => !p.is_out);
      if (available.length >= 1) {
        this.strikerId = available[0].id;
        this.el.strikerSelect.value = this.strikerId;
      }
      if (available.length >= 2) {
        this.nonStrikerId = available[1].id;
        this.el.nonStrikerSelect.value = this.nonStrikerId;
      }
    }
    if (!this.bowlerId && inn.bowling_players.length >= 1) {
      this.bowlerId = inn.bowling_players[0].id;
      this.el.bowlerSelect.value = this.bowlerId;
    }
  }

  renderStatsTables(inningsData) {
    if (!inningsData) return;

    if (this.el.battingTable) {
      this.el.battingTable.innerHTML = inningsData.batsmen.map(p => `
        <tr class="${p.is_out ? 'out' : ''}">
          <td>${p.name}${p.is_out ? ' †' : ' *'}</td>
          <td class="highlight">${p.runs}</td>
          <td>${p.balls}</td>
          <td>${p.fours}</td>
          <td>${p.sixes}</td>
        </tr>
      `).join('');
    }

    if (this.el.bowlingTable) {
      this.el.bowlingTable.innerHTML = inningsData.bowlers
        .filter(p => p.balls_bowled > 0 || p.wickets > 0)
        .map(p => `
        <tr>
          <td>${p.name}</td>
          <td>${p.overs}</td>
          <td class="highlight">${p.wickets}</td>
          <td>${p.runs_conceded}</td>
        </tr>
      `).join('') || '<tr><td colspan="4" class="text-center opacity-50">No bowling data yet</td></tr>';
    }
  }

  updateButtonState() {
    const enabled = this.canScore();
    if (this.el.runButtons) {
      this.el.runButtons.querySelectorAll('button').forEach(btn => {
        btn.disabled = !enabled;
      });
    }
  }

  parseAction(action) {
    const map = {
      '0': { runs: 0, extras: 'none' },
      '1': { runs: 1, extras: 'none' },
      '2': { runs: 2, extras: 'none' },
      '3': { runs: 3, extras: 'none' },
      '4': { runs: 4, extras: 'none' },
      '6': { runs: 6, extras: 'none' },
      'wide': { runs: 0, extras: 'wide' },
      'no_ball': { runs: 0, extras: 'no_ball' },
      'bye': { runs: 1, extras: 'bye' },
    };
    return map[action] || { runs: 0, extras: 'none' };
  }

  async recordBall(action, wicketData = null) {
    if (!this.canScore() && !wicketData) return;

    const inn = this.getCurrentInnings();
    const parsed = wicketData || this.parseAction(action);

    const payload = {
      innings_id: inn.id,
      batsman_id: this.strikerId,
      non_striker_id: this.nonStrikerId,
      bowler_id: this.bowlerId,
      runs: parsed.runs,
      extras: parsed.extras,
      is_wicket: !!wicketData,
      wicket_type: wicketData?.wicket_type || '',
      fielder_id: wicketData?.fielder_id || null,
    };

    try {
      const res = await fetch(this.scoreUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken,
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.error) {
        alert(data.error);
        return;
      }

      if (data.state) {
        this.state = data.state;
      }

      if (data.striker_id) {
        this.strikerId = data.striker_id;
        if (this.el.strikerSelect) this.el.strikerSelect.value = data.striker_id;
      } else if (wicketData) {
        this.strikerId = null;
        if (this.el.strikerSelect) this.el.strikerSelect.value = '';
      }

      if (data.non_striker_id) {
        this.nonStrikerId = data.non_striker_id;
        if (this.el.nonStrikerSelect) this.el.nonStrikerSelect.value = data.non_striker_id;
      }

      this.render();

      if (data.status === 'innings_completed' || data.status === 'match_completed') {
        setTimeout(() => {
          if (data.status === 'match_completed') {
            window.location.href = `/cricket/match/${this.matchId}/scoreboard/`;
          } else {
            alert('Innings complete! Second innings starting.');
            window.location.reload();
          }
        }, 800);
      }
    } catch (err) {
      alert('Scoring failed: ' + err.message);
    }
  }

  showWicketModal() {
    const modal = document.getElementById('wicketModal');
    if (modal) {
      const bsModal = bootstrap.Modal.getOrCreateInstance(modal);
      document.querySelectorAll('[data-wicket-type]').forEach(b => b.classList.remove('active'));
      const first = document.querySelector('[data-wicket-type="caught"]');
      if (first) first.classList.add('active');
      if (this.el.fielderGroup) this.el.fielderGroup.style.display = 'block';
      bsModal.show();
    }
  }

  confirmWicket() {
    const active = document.querySelector('[data-wicket-type].active');
    if (!active) return;
    const wicketType = active.dataset.wicketType;
    const fielderId = ['caught', 'run_out', 'stumped'].includes(wicketType)
      ? parseInt(this.el.fielderSelect?.value) || null
      : null;

    const modal = document.getElementById('wicketModal');
    if (modal) bootstrap.Modal.getInstance(modal)?.hide();

    this.recordBall(null, {
      runs: 0,
      extras: 'none',
      wicket_type: wicketType,
      fielder_id: fielderId,
    });
  }
}

window.CricketScorer = CricketScorer;
