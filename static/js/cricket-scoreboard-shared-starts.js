// Shared compact stats helpers for cricket live scoring

window.cricketShared = {
  formatOversFromBalls(oversStr) {
    return oversStr || '0.0';
  },

  formatBallsText(balls) {
    if (balls === null || balls === undefined) return '0';
    return String(balls);
  },
};

