const AI_DIFFICULTY = {
  easy: 0.3,
  medium: 0.6,
  hard: 0.9
};

function aiChooseMove(strongMoves, allMoves, difficultyLevel) {
  const pSmart = AI_DIFFICULTY[difficultyLevel] ?? AI_DIFFICULTY.medium;
  const useSmart = Math.random() < pSmart && strongMoves.length > 0;

  if (useSmart) {
    return strongMoves[Math.floor(Math.random() * strongMoves.length)];
  } else {
    return allMoves[Math.floor(Math.random() * allMoves.length)];
  }
}
