const firebaseConfig = {
  apiKey: "AIzaSyDc3-2LTaUFsxmCYjgZvKvURFh_MY3lFX4",
  authDomain: "games-html.firebaseapp.com",
  databaseURL: "https://games-html-default-rtdb.firebaseio.com",
  projectId: "games-html",
  storageBucket: "games-html.firebasestorage.app",
  messagingSenderId: "981720658246",
  appId: "1:981720658246:web:02c98b33e7885961aff547",
  measurementId: "G-YHV59EV8E7"
};

if (!firebase.apps || !firebase.apps.length) {
  firebase.initializeApp(firebaseConfig);
}

const db = firebase.database();
