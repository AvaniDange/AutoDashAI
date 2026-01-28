import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyB71ztKDyNyiX08jc23QAi4LqtWvw-cTP8",
  authDomain: "autodashai.firebaseapp.com",
  projectId: "autodashai",
  storageBucket: "autodashai.firebasestorage.app",
  messagingSenderId: "319077379925",
  appId: "1:319077379925:web:28598830e32eff1d2589dc",
  measurementId: "G-TFR5PZBNCG"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export { auth };