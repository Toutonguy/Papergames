src="https://www.gstatic.com/firebasejs/8.10.0/firebase-app.js">
src="https://www.gstatic.com/firebasejs/8.10.0/firebase-database.js">

src="../scripts/firebase-config.js">
function createRoom(gameName) {
  const roomId = Math.random().toString(36).substring(2, 8);
  const ref = db.ref(`games/${gameName}/rooms/${roomId}`);
  ref.set({ createdAt: Date.now() });
  return roomId;
}

function joinRoom(gameName, roomId) {
  return db.ref(`games/${gameName}/rooms/${roomId}`).get();
}

function sendMove(gameName, roomId, moveObj) {
  const movesRef = db.ref(`games/${gameName}/rooms/${roomId}/moves`);
  movesRef.push({ ...moveObj, t: Date.now() });
}

function onMove(gameName, roomId, callback) {
  const movesRef = db.ref(`games/${gameName}/rooms/${roomId}/moves`);
  movesRef.on("child_added", snap => callback(snap.val()));
}
  
